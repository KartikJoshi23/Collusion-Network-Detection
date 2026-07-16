"""Training loops, losses, samplers (§4.4) + config-driven baseline runs (§7 step 10)."""

from .baseline_run import assemble_features, raw_feature_frame, run_baselines

__all__ = ["assemble_features", "raw_feature_frame", "run_baselines"]
