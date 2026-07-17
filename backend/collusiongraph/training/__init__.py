"""Training: losses, graph build, GNN trainer, alert queue, baseline runs (§4.4, §7)."""

from .alert_queue import build_alert_queue
from .baseline_run import assemble_features, raw_feature_frame, run_baselines
from .graph_build import build_graph, confirmed_mask_for
from .losses import focal_loss, make_loss, weighted_ce_loss
from .trainer import train_gnn

__all__ = [
    "assemble_features",
    "build_alert_queue",
    "build_graph",
    "confirmed_mask_for",
    "focal_loss",
    "make_loss",
    "raw_feature_frame",
    "run_baselines",
    "train_gnn",
    "weighted_ce_loss",
]

from .ensemble_run import run_ensemble, run_injection_recovery

__all__ += ["run_ensemble", "run_injection_recovery"]

from .labels import resolve_train_labels  # noqa: E402

__all__ += ["resolve_train_labels"]

from .transfer_run import run_cross_domain_probe, run_loco_transfer  # noqa: E402

__all__ += ["run_cross_domain_probe", "run_loco_transfer"]
