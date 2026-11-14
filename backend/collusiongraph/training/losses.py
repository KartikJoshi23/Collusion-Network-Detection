"""Imbalance-aware losses (§4.4): focal loss vs class-weighted cross-entropy.

The two are the head-to-head ablation RQ1 demands — both operate on binary
logits over CONFIRMED nodes only (unknowns carry structure, never gradient;
§4.3 D1).
"""

from __future__ import annotations

from collections.abc import Callable

import torch
import torch.nn.functional as F

LossFn = Callable[[torch.Tensor, torch.Tensor], torch.Tensor]


def focal_loss(
    logits: torch.Tensor,
    targets: torch.Tensor,
    gamma: float = 2.0,
    alpha: float | None = None,
    label_smoothing: float = 0.0,
) -> torch.Tensor:
    """Binary focal loss on logits (Lin et al. 2017): CE scaled by (1-p_t)^γ.

    ``gamma=0`` recovers (α-weighted) cross-entropy exactly — the property the
    unit tests pin. ``alpha`` is the positive-class weight ∈ (0, 1); None means
    unweighted. ``label_smoothing`` = ε moves the cross-entropy targets to
    y(1 − ε) + ε/2. The focal weight keeps the hard targets, and ε = 0
    reproduces the published loss exactly (revision brief item B7).
    """
    if not 0.0 <= label_smoothing < 1.0:
        raise ValueError(f"label_smoothing must be in [0, 1), got {label_smoothing}")
    targets = targets.float()
    soft = targets * (1.0 - label_smoothing) + 0.5 * label_smoothing
    ce = F.binary_cross_entropy_with_logits(logits, soft, reduction="none")
    p = torch.sigmoid(logits)
    p_t = p * targets + (1 - p) * (1 - targets)
    loss = ce * (1 - p_t).pow(gamma)
    if alpha is not None:
        alpha_t = alpha * targets + (1 - alpha) * (1 - targets)
        loss = alpha_t * loss
    return loss.mean()


def weighted_ce_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """Class-weighted BCE: positive class up-weighted by neg/pos of THIS batch
    (the classical imbalance handling focal loss is ablated against)."""
    targets = targets.float()
    n_pos = targets.sum()
    n_neg = targets.numel() - n_pos
    if n_pos == 0 or n_neg == 0:
        return F.binary_cross_entropy_with_logits(logits, targets)
    return F.binary_cross_entropy_with_logits(logits, targets, pos_weight=n_neg / n_pos)


def make_loss(name: str, **kwargs: float) -> LossFn:
    if name == "focal":
        gamma = kwargs.get("gamma", 2.0)
        alpha = kwargs.get("alpha")
        smoothing = float(kwargs.get("label_smoothing", 0.0))
        return lambda logits, targets: focal_loss(
            logits, targets, gamma=gamma, alpha=alpha, label_smoothing=smoothing
        )
    if name == "weighted_ce":
        return weighted_ce_loss
    raise ValueError(f"unknown loss {name!r} (expected 'focal' or 'weighted_ce')")
