"""
Neural network baseline: 3-layer feedforward NN (GKX architecture).

Uses PyTorch. Architecture: input → 32 → 16 → 8 → 1
with ReLU, batch normalization, dropout, and early stopping.
"""
import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def _check_torch():
    if not HAS_TORCH:
        raise ImportError(
            "PyTorch is required for NeuralNetModel. "
            "Install with: pip install torch"
        )


class _GKXNet(nn.Module):
    """3-layer feedforward network following Gu-Kelly-Xiu (2020)."""

    def __init__(self, input_dim: int, dropout: float = 0.5):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 16),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(16, 8),
            nn.BatchNorm1d(8),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(8, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


class NeuralNetModel:
    """
    GKX-style 3-layer feedforward neural network.

    Parameters
    ----------
    lr : learning rate
    epochs : maximum training epochs
    batch_size : mini-batch size
    dropout : dropout rate
    patience : early stopping patience
    """

    def __init__(
        self,
        lr: float = 0.001,
        epochs: int = 100,
        batch_size: int = 256,
        dropout: float = 0.5,
        patience: int = 5,
        random_state: int = 42,
    ):
        _check_torch()
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.dropout = dropout
        self.patience = patience
        self.random_state = random_state
        self.model_ = None
        self.mean_ = None
        self.std_ = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def _standardize_fit(self, X: np.ndarray):
        self.mean_ = X.mean(axis=0)
        self.std_ = X.std(axis=0)
        self.std_[self.std_ == 0] = 1.0
        return (X - self.mean_) / self.std_

    def _standardize_transform(self, X: np.ndarray):
        return (X - self.mean_) / self.std_

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_val: np.ndarray | None = None,
        y_val: np.ndarray | None = None,
        **kwargs,
    ):
        _check_torch()
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        X_sc = self._standardize_fit(X)

        # If no validation set, hold out last 20% temporally
        if X_val is None:
            n = len(X_sc)
            split = int(0.8 * n)
            X_val_sc = X_sc[split:]
            y_val_use = y[split:]
            X_sc = X_sc[:split]
            y = y[:split]
        else:
            X_val_sc = self._standardize_transform(X_val)
            y_val_use = y_val

        X_t = torch.tensor(X_sc, dtype=torch.float32).to(self.device)
        y_t = torch.tensor(y, dtype=torch.float32).to(self.device)
        X_val_t = torch.tensor(X_val_sc, dtype=torch.float32).to(self.device)
        y_val_t = torch.tensor(y_val_use, dtype=torch.float32).to(self.device)

        dataset = TensorDataset(X_t, y_t)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)

        self.model_ = _GKXNet(X_sc.shape[1], dropout=self.dropout).to(self.device)
        optimizer = torch.optim.Adam(self.model_.parameters(), lr=self.lr)
        criterion = nn.MSELoss()

        best_val_loss = np.inf
        patience_counter = 0
        best_state = None

        for epoch in range(self.epochs):
            self.model_.train()
            for X_batch, y_batch in loader:
                optimizer.zero_grad()
                pred = self.model_(X_batch)
                loss = criterion(pred, y_batch)
                loss.backward()
                optimizer.step()

            # Validation
            self.model_.eval()
            with torch.no_grad():
                val_pred = self.model_(X_val_t)
                val_loss = criterion(val_pred, y_val_t).item()

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_state = {k: v.cpu().clone() for k, v in self.model_.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= self.patience:
                    break

        if best_state is not None:
            self.model_.load_state_dict(best_state)
            self.model_.to(self.device)

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        _check_torch()
        X_sc = self._standardize_transform(X)
        X_t = torch.tensor(X_sc, dtype=torch.float32).to(self.device)
        self.model_.eval()
        with torch.no_grad():
            pred = self.model_(X_t).cpu().numpy()
        return pred

    def tune(
        self,
        X: np.ndarray,
        y: np.ndarray,
        cv_splits: list[tuple[np.ndarray, np.ndarray]],
        **kwargs,
    ) -> dict:
        """Tune learning rate and dropout via LOYO CV (limited grid)."""
        lr_grid = [0.01, 0.001, 0.0001]
        dropout_grid = [0.3, 0.5]

        best_lr = self.lr
        best_do = self.dropout
        best_mse = np.inf

        for lr in lr_grid:
            for do in dropout_grid:
                mse_folds = []
                for train_idx, val_idx in cv_splits:
                    model = NeuralNetModel(
                        lr=lr, epochs=self.epochs, batch_size=self.batch_size,
                        dropout=do, patience=self.patience, random_state=self.random_state,
                    )
                    model.fit(X[train_idx], y[train_idx], X[val_idx], y[val_idx])
                    pred = model.predict(X[val_idx])
                    mse_folds.append(np.mean((y[val_idx] - pred) ** 2))
                avg_mse = np.mean(mse_folds)
                if avg_mse < best_mse:
                    best_mse = avg_mse
                    best_lr = lr
                    best_do = do

        self.lr = best_lr
        self.dropout = best_do
        self.fit(X, y)
        return {'lr': best_lr, 'dropout': best_do, 'cv_mse': best_mse}
