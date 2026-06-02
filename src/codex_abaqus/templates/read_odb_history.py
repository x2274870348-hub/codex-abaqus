"""Template script for reading ODB history output. Outputs JSON to stdout.

Expected environment variables:
    ODB_PATH: path to the .odb file
    HISTORY_NAMES: comma-separated history output names (e.g., "U2 at Node 10", "RF1")
    STEP_INDEX: which step to read (0-based, default 0)
"""

import os
import sys
import json
import traceback

try:
    from odbAccess import openOdb

    odb_path = os.environ.get("ODB_PATH")
    history_names = os.environ.get("HISTORY_NAMES", "")
    step_idx = int(os.environ.get("STEP_INDEX", "0"))

    if not odb_path:
        print(json.dumps({"error": "ODB_PATH not set"}))
        sys.exit(1)

    odb = openOdb(path=odb_path, readOnly=True)

    steps = list(odb.steps.keys())
    if step_idx >= len(steps):
        result = {"error": f"Step index out of range", "available_steps": steps}
    else:
        step_name = steps[step_idx]
        step = odb.steps[step_name]

        # List all available history regions
        all_history = {}
        for region_name in step.historyRegions.keys():
            region = step.historyRegions[region_name]
            all_history[region_name] = list(region.historyOutputs.keys())

        if not history_names:
            result = {
                "odb_path": odb_path,
                "step": step_name,
                "available_history": all_history,
            }
        else:
            requested = [h.strip() for h in history_names.split(",") if h.strip()]
            result = {
                "odb_path": odb_path,
                "step": step_name,
                "history": {},
            }

            for region_name, region in step.historyRegions.items():
                for ho_name in requested:
                    if ho_name in region.historyOutputs:
                        ho = region.historyOutputs[ho_name]
                        data = [(t, v) for t, v in zip(ho.data[0], ho.data[1]) if hasattr(ho, "data")]
                        # fallback: iterate
                        if not data:
                            data = []
                            for frame in ho.data:
                                data.append([frame[0], frame[1]])
                        result["history"][f"{region_name}:{ho_name}"] = {
                            "description": ho.description,
                            "type": str(ho.type),
                            "data": data,
                        }

    odb.close()
    print(json.dumps(result, default=str))

except Exception as e:
    print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}, default=str))
    sys.exit(1)
