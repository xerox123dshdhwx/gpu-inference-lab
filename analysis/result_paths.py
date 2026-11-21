from pathlib import Path


BASELINE_FOLDER = "baseline (vLLM)"


def results_directory(name):
    directory = Path("results") / name
    if name == "baseline" and not directory.exists():
        return directory.with_name(BASELINE_FOLDER)
    return directory
