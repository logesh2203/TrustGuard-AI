import os
import pandas as pd
import random
from typing import Optional, Dict, Any, List
from backend.config import Config

class DatasetService:
    """Service to load and query the creditcard.csv dataset."""

    _df: Optional[pd.DataFrame] = None
    _initialized: bool = False

    REQUIRED_COLUMNS = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount', 'Class']

    @classmethod
    def get_dataset_path(cls) -> str:
        return Config.DATASET_PATH

    @classmethod
    def is_dataset_available(cls) -> bool:
        return os.path.isfile(cls.get_dataset_path())

    @classmethod
    def load_dataset(cls) -> pd.DataFrame:
        """Load and validate the dataset with lazy singleton loading."""
        if cls._df is not None:
            return cls._df

        dataset_path = cls.get_dataset_path()
        if not os.path.isfile(dataset_path):
            raise FileNotFoundError(
                f"Dataset file not found at '{dataset_path}'. "
                f"Please ensure data/creditcard.csv is placed in the project root."
            )

        try:
            df = pd.read_csv(dataset_path)
            missing_cols = [col for col in cls.REQUIRED_COLUMNS if col not in df.columns]
            if missing_cols:
                raise ValueError(
                    f"Dataset is missing required columns: {', '.join(missing_cols)}"
                )

            cls._df = df
            cls._initialized = True
            return cls._df
        except Exception as e:
            raise RuntimeError(f"Error loading creditcard.csv dataset: {str(e)}")

    @classmethod
    def get_sample_transactions_for_user(
        cls, 
        normal_count: int = 12, 
        fraud_count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Sample a balanced set of normal and fraud transactions from the dataset
        to initialize a newly registered customer's account.
        """
        df = cls.load_dataset()

        normal_df = df[df['Class'] == 0]
        fraud_df = df[df['Class'] == 1]

        # Sample normal and fraud records
        sampled_normal = normal_df.sample(n=min(normal_count, len(normal_df)), random_state=random.randint(1, 10000))
        sampled_fraud = fraud_df.sample(n=min(fraud_count, len(fraud_df)), random_state=random.randint(1, 10000))

        # Combine and sort by Time
        combined = pd.concat([sampled_normal, sampled_fraud]).sort_values(by='Time')

        transactions = []
        for row_index, row in combined.iterrows():
            transactions.append({
                'dataset_row_id': int(row_index),
                'amount': float(row['Amount']),
                'transaction_time': float(row['Time']),
                'class_label': int(row['Class'])
            })

        return transactions

    @classmethod
    def get_transaction_features(cls, dataset_row_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve the full feature set (V1-V28, Time, Amount, Class) for a specific row index.
        """
        df = cls.load_dataset()

        if dataset_row_id < 0 or dataset_row_id >= len(df):
            return None

        row = df.iloc[dataset_row_id]

        v_features = {
            f'V{i}': round(float(row[f'V{i}']), 6) 
            for i in range(1, 29)
        }

        amt = round(float(row['Amount']), 2)
        cls_lbl = int(row['Class'])
        risk = 'HIGH' if cls_lbl == 1 else ('MEDIUM' if amt >= 500 else 'LOW')

        return {
            'dataset_row_id': int(dataset_row_id),
            'time': float(row['Time']),
            'amount': amt,
            'class_label': cls_lbl,
            'status': 'Normal' if cls_lbl == 0 else 'Fraud-Labeled',
            'risk_level': risk,
            'features': v_features
        }

    @classmethod
    def get_dataset_summary_stats(cls) -> Dict[str, Any]:
        """
        Compute aggregate statistics for the entire creditcard.csv dataset.
        """
        df = cls.load_dataset()
        total = int(len(df))
        fraud = int((df['Class'] == 1).sum())
        normal = total - fraud
        fraud_pct = round((fraud / total) * 100, 3) if total > 0 else 0.0

        return {
            'total_transactions': total,
            'normal_transactions': normal,
            'fraud_transactions': fraud,
            'fraud_percentage': fraud_pct
        }

    @classmethod
    def get_paginated_dataset_transactions(
        cls,
        page: int = 1,
        per_page: int = 20,
        status: str = 'all',
        search_id: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        risk_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve paginated slice of dataset transactions with advanced search, status, amount range, and risk filters.
        """
        df = cls.load_dataset()
        filtered_df = df

        # Apply status filter
        if status in ('0', 'normal'):
            filtered_df = filtered_df[filtered_df['Class'] == 0]
        elif status in ('1', 'fraud', 'fraud-labeled'):
            filtered_df = filtered_df[filtered_df['Class'] == 1]

        # Apply amount range filters
        if min_amount is not None:
            filtered_df = filtered_df[filtered_df['Amount'] >= min_amount]
        if max_amount is not None:
            filtered_df = filtered_df[filtered_df['Amount'] <= max_amount]

        # Apply risk filter (Class 1 = HIGH, Class 0 + Amount >= 500 = MEDIUM, Class 0 + Amount < 500 = LOW)
        if risk_level:
            rl = risk_level.strip().upper()
            if rl == 'HIGH':
                filtered_df = filtered_df[filtered_df['Class'] == 1]
            elif rl == 'MEDIUM':
                filtered_df = filtered_df[(filtered_df['Class'] == 0) & (filtered_df['Amount'] >= 500)]
            elif rl == 'LOW':
                filtered_df = filtered_df[(filtered_df['Class'] == 0) & (filtered_df['Amount'] < 500)]

        # Apply search by row index / ID or exact amount
        if search_id is not None and str(search_id).strip():
            s = str(search_id).strip()
            if s.isdigit():
                idx = int(s)
                if idx in filtered_df.index:
                    filtered_df = filtered_df.loc[[idx]]
                else:
                    filtered_df = filtered_df.iloc[0:0]  # Empty
            else:
                try:
                    amt = float(s)
                    filtered_df = filtered_df[filtered_df['Amount'] == amt]
                except ValueError:
                    filtered_df = filtered_df.iloc[0:0]

        total_count = int(len(filtered_df))
        total_pages = max(1, (total_count + per_page - 1) // per_page)
        page = max(1, min(page, total_pages)) if total_count > 0 else 1
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        sliced_df = filtered_df.iloc[start_idx:end_idx]

        records = []
        for row_index, row in sliced_df.iterrows():
            amt = round(float(row['Amount']), 2)
            cls_lbl = int(row['Class'])
            risk = 'HIGH' if cls_lbl == 1 else ('MEDIUM' if amt >= 500 else 'LOW')
            records.append({
                'id': int(row_index),
                'dataset_row_id': int(row_index),
                'amount': amt,
                'transaction_time': float(row['Time']),
                'class_label': cls_lbl,
                'risk_level': risk,
                'status': 'Normal' if cls_lbl == 0 else 'Fraud-Labeled'
            })

        return {
            'transactions': records,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        }

    @classmethod
    def get_recent_dataset_transactions(cls, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve recent transactions from dataset sample."""
        df = cls.load_dataset()
        records = []
        for row_index, row in df.head(limit).iterrows():
            amt = round(float(row['Amount']), 2)
            cls_lbl = int(row['Class'])
            risk = 'HIGH' if cls_lbl == 1 else ('MEDIUM' if amt >= 500 else 'LOW')
            records.append({
                'id': int(row_index),
                'dataset_row_id': int(row_index),
                'amount': amt,
                'transaction_time': float(row['Time']),
                'class_label': cls_lbl,
                'risk_level': risk,
                'status': 'Normal' if cls_lbl == 0 else 'Fraud-Labeled'
            })
        return records

