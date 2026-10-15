"""Explicit sensor rules; missing measurements never become normal evidence."""

import math

import numpy as np


def validate_rule(rule: dict, sensors: dict) -> None:
    name = rule.get("sensor")
    if name not in sensors or not sensors[name].get("enabled", True):
        raise ValueError("Rule requires an enabled sensor")
    if rule.get("operator") not in {"gt", "ge", "lt", "le", "eq", "outside", "inside"}:
        raise ValueError("Rule requires an explicit comparison operator")
    unit = sensors[name].get("unit")
    if unit is not None and rule.get("unit") != unit:
        raise ValueError("Rule unit must match the confirmed sensor unit")
    keys = ("lower", "upper") if rule["operator"] in {"outside", "inside"} else ("value",)
    for key in keys:
        value = rule.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Rule requires finite explicit limits")
    if len(keys) == 2 and rule["lower"] > rule["upper"]:
        raise ValueError("Rule lower limit exceeds upper limit")
    reference = rule.get("reference_sensor")
    if reference is not None and (unit is None or reference not in sensors or sensors[reference].get("unit") != unit):
        raise ValueError("Difference rule requires a reference sensor with the same unit")


def compare(values, rule: dict):
    op = rule["operator"]
    if op == "gt": return values > rule["value"]
    if op == "ge": return values >= rule["value"]
    if op == "lt": return values < rule["value"]
    if op == "le": return values <= rule["value"]
    if op == "eq": return values == rule["value"]
    inside = (values >= rule["lower"]) & (values <= rule["upper"])
    return ~inside if op == "outside" else inside


def evaluate_rules(values: dict, rules: list[dict], *, combination="any") -> dict:
    if combination not in {"any", "all"}: raise ValueError("Invalid rule combination")
    details = []
    for rule in rules:
        value = values.get(rule["sensor"])
        reference = values.get(rule["reference_sensor"]) if rule.get("reference_sensor") else 0
        available = all(isinstance(v, (int, float, np.number)) and not isinstance(v, (bool, np.bool_)) and np.isfinite(v) for v in (value, reference))
        checked = float(value - reference) if available else None
        details.append({"sensor": rule["sensor"], "operator": rule["operator"], "checked_value": checked,
                        "condition_met": bool(compare(checked, rule)) if available else None})
    flags = [item["condition_met"] for item in details]
    result = None
    # Three-valued logic preserves decisive evidence without hiding unknown inputs.
    if flags:
        if combination == "any": result = True if True in flags else None if None in flags else False
        else: result = False if False in flags else None if None in flags else True
    return {"condition_met": result, "details": details, "combination": combination}
