"""
claim_parser.py - Robust Claims Data Parser

Parses messy machine-parsed claim JSON files into structured, strongly typed Python objects.
Gracefully handles missing, null, zero-value, or unexpected fields without crashing,
defaulting missing visual values to "not available" as specified in requirements.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json
import os

NOT_AVAILABLE = "not available"

def safe_str(value: Any, default: str = NOT_AVAILABLE) -> str:
    """Returns string representation, or default if missing/null/empty."""
    if value is None:
        return default
    s = str(value).strip()
    return s if s != "" else default

def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Safely converts value to float or returns default if None/invalid."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Safely converts value to int or returns default if None/invalid."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def format_currency(value: Optional[float], currency_symbol: str = "₹") -> str:
    """Formats numeric value as currency string or 'not available' if None."""
    if value is None:
        return NOT_AVAILABLE
    try:
        val = float(value)
        return f"{currency_symbol}{val:,.2f}"
    except (ValueError, TypeError):
        return NOT_AVAILABLE

def format_percent(value: Optional[float]) -> str:
    """Formats numeric value as percentage or 'not available' if None."""
    if value is None:
        return NOT_AVAILABLE
    try:
        val = float(value)
        return f"{val:g}%"
    except (ValueError, TypeError):
        return NOT_AVAILABLE


@dataclass
class EstimateLineItem:
    part_name: str
    part_type: str
    quantity: int
    part_total: Optional[float]           # Stated base total for part
    part_dep_perc: Optional[float]
    part_gst_perc: Optional[float]
    total_part_amt: Optional[float]       # Claims system line part total
    total_labour_amt: Optional[float]     # Claims system line labour total
    total_final_amt: Optional[float]      # Claims system line final total
    calculated_final_amt: Optional[float] # Dynamically calculated amount with GST & Dep

    @property
    def formatted_quantity(self) -> str:
        return str(self.quantity)

    @property
    def formatted_part_total(self) -> str:
        return format_currency(self.part_total)

    @property
    def formatted_dep_perc(self) -> str:
        return format_percent(self.part_dep_perc)

    @property
    def formatted_gst_perc(self) -> str:
        return format_percent(self.part_gst_perc)

    @property
    def formatted_final_amt(self) -> str:
        if self.total_final_amt is not None:
            return format_currency(self.total_final_amt)
        if self.calculated_final_amt is not None:
            return format_currency(self.calculated_final_amt)
        return NOT_AVAILABLE


@dataclass
class DamagePhotoPart:
    parts_name: str
    damage_type: str


@dataclass
class ClaimsSystemAmounts:
    estimated_amount_listed: Optional[float]
    final_settled_amount: Optional[float]
    currency: str


@dataclass
class ParsedEstimateSummary:
    stated_total_estimate_cost: Optional[float]
    total_part_estimation_cost: Optional[float]
    labour_estimation_cost: Optional[float]
    paint_estimation_cost: Optional[float]
    vehicle_age_depreciation_pct: Optional[float]
    lines: List[EstimateLineItem] = field(default_factory=list)
    parsed_damage_parts_from_photos: List[DamagePhotoPart] = field(default_factory=list)


@dataclass
class ClaimData:
    claim_ref: str
    vehicle: str
    loss_date: str
    loss_summary: str
    nature_of_loss: str
    payment_mode: str
    source_note: str
    claims_system_amounts: ClaimsSystemAmounts
    parsed_estimate: ParsedEstimateSummary
    raw_json: Dict[str, Any] = field(default_factory=dict)

    # Helper getters with default fallbacks
    @property
    def formatted_claim_ref(self) -> str:
        return safe_str(self.claim_ref)

    @property
    def formatted_vehicle(self) -> str:
        return safe_str(self.vehicle)

    @property
    def formatted_loss_date(self) -> str:
        return safe_str(self.loss_date)

    @property
    def formatted_loss_summary(self) -> str:
        return safe_str(self.loss_summary)

    @property
    def formatted_nature_of_loss(self) -> str:
        return safe_str(self.nature_of_loss)

    @property
    def formatted_payment_mode(self) -> str:
        return safe_str(self.payment_mode)


def parse_claim_json(file_path_or_dict: Any) -> ClaimData:
    """
    Parses a claim JSON file or dictionary into a structured ClaimData object.
    Never raises an exception on bad/missing fields; returns safe defaults.
    """
    if isinstance(file_path_or_dict, (str, os.PathLike)):
        with open(file_path_or_dict, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif isinstance(file_path_or_dict, dict):
        data = file_path_or_dict
    else:
        data = {}

    claim_ref = safe_str(data.get("claim_ref"), default="UNKNOWN-CLAIM")
    vehicle = safe_str(data.get("vehicle"), default=NOT_AVAILABLE)
    loss_date = safe_str(data.get("loss_date"), default=NOT_AVAILABLE)
    loss_summary = safe_str(data.get("loss_summary"), default=NOT_AVAILABLE)
    nature_of_loss = safe_str(data.get("nature_of_loss"), default=NOT_AVAILABLE)
    payment_mode = safe_str(data.get("payment_mode"), default=NOT_AVAILABLE)
    source_note = safe_str(data.get("source_note"), default=NOT_AVAILABLE)

    # Claims System Amounts
    cs_dict = data.get("claims_system_amounts") or {}
    cs_amounts = ClaimsSystemAmounts(
        estimated_amount_listed=safe_float(cs_dict.get("estimated_amount_listed")),
        final_settled_amount=safe_float(cs_dict.get("final_settled_amount")),
        currency=safe_str(cs_dict.get("currency"), default="INR")
    )

    # Parsed Estimate
    pe_dict = data.get("parsed_estimate") or {}
    stated_total = safe_float(pe_dict.get("stated_total_estimate_cost"))
    total_part = safe_float(pe_dict.get("total_part_estimation_cost"))
    labour_cost = safe_float(pe_dict.get("labour_estimation_cost"))
    paint_cost = safe_float(pe_dict.get("paint_estimation_cost"))
    vehicle_dep = safe_float(pe_dict.get("vehicle_age_depreciation_pct"))

    raw_lines = pe_dict.get("lines") or []
    lines: List[EstimateLineItem] = []

    for item in raw_lines:
        if not isinstance(item, dict):
            continue

        p_name = safe_str(item.get("part_name"), default="Unnamed Part/Service")
        p_type = safe_str(item.get("part_type"), default="Other")
        qty = safe_int(item.get("part_quantity"), default=1)
        if qty is None or qty <= 0:
            qty = 1

        p_total = safe_float(item.get("part_total"))
        p_dep = safe_float(item.get("part_dep_perc"), default=vehicle_dep)
        p_gst = safe_float(item.get("part_gst_perc"))
        
        t_part = safe_float(item.get("total_part_amt"))
        t_labour = safe_float(item.get("total_labour_amt"))
        t_final = safe_float(item.get("total_final_amt"))

        # Calculate line final amount if not provided
        calc_final = None
        if p_total is not None:
            dep_rate = (p_dep / 100.0) if p_dep is not None else 0.0
            gst_rate = (p_gst / 100.0) if p_gst is not None else 0.0
            # Standard auto claim formula: Total = Base * (1 - Dep%) * (1 + GST%)
            # If no GST specified or 0, simple depreciated amount
            depreciated_amount = p_total * (1.0 - dep_rate)
            calc_final = depreciated_amount * (1.0 + gst_rate)

        lines.append(
            EstimateLineItem(
                part_name=p_name,
                part_type=p_type,
                quantity=qty,
                part_total=p_total,
                part_dep_perc=p_dep,
                part_gst_perc=p_gst,
                total_part_amt=t_part,
                total_labour_amt=t_labour,
                total_final_amt=t_final,
                calculated_final_amt=calc_final
            )
        )

    # Damage parts from photos
    photos_list = pe_dict.get("parsed_damage_parts_from_photos") or []
    damage_parts: List[DamagePhotoPart] = []
    for photo in photos_list:
        if isinstance(photo, dict):
            damage_parts.append(
                DamagePhotoPart(
                    parts_name=safe_str(photo.get("parts_name")),
                    damage_type=safe_str(photo.get("damage_type"))
                )
            )

    parsed_est = ParsedEstimateSummary(
        stated_total_estimate_cost=stated_total,
        total_part_estimation_cost=total_part,
        labour_estimation_cost=labour_cost,
        paint_estimation_cost=paint_cost,
        vehicle_age_depreciation_pct=vehicle_dep,
        lines=lines,
        parsed_damage_parts_from_photos=damage_parts
    )

    return ClaimData(
        claim_ref=claim_ref,
        vehicle=vehicle,
        loss_date=loss_date,
        loss_summary=loss_summary,
        nature_of_loss=nature_of_loss,
        payment_mode=payment_mode,
        source_note=source_note,
        claims_system_amounts=cs_amounts,
        parsed_estimate=parsed_est,
        raw_json=data if isinstance(data, dict) else {}
    )
