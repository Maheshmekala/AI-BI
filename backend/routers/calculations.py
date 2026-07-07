"""REST endpoints for calculated field CRUD operations."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.state import state
from backend.schemas import (
    CalculatedFieldCreate, CalculatedFieldPreview,
    CalculatedFieldPreviewResponse, CalculatedFieldValidateResponse,
    CalculatedFieldInfo,
)
from backend.calculations.engine import BackendCalculatedFieldEngine

router = APIRouter()
calc_engine = BackendCalculatedFieldEngine()


@router.post("/datasets/{ds_id}/calculated-fields")
async def create_calculated_field(ds_id: str, req: CalculatedFieldCreate):
    """Create a new calculated field for a dataset."""
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    try:
        result = calc_engine.create_field(ds, req.name, req.expression)
        return result
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.get("/datasets/{ds_id}/calculated-fields")
async def list_calculated_fields(ds_id: str):
    """List all calculated fields for a dataset."""
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")
    return calc_engine.get_fields(ds)


@router.delete("/datasets/{ds_id}/calculated-fields/{field_name}")
async def delete_calculated_field(ds_id: str, field_name: str):
    """Remove a calculated field."""
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    if calc_engine.remove_field(ds, field_name):
        return {"status": "ok", "message": f"Field '{field_name}' removed"}
    raise HTTPException(404, f"Field '{field_name}' not found")


@router.post("/datasets/{ds_id}/calculated-fields/preview")
async def preview_calculated_field(ds_id: str, req: CalculatedFieldPreview):
    """Preview the result of an expression."""
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    result = calc_engine.preview_expression(req.expression, ds, req.limit)
    return result


@router.post("/datasets/{ds_id}/calculated-fields/validate")
async def validate_calculated_field(ds_id: str, req: CalculatedFieldCreate):
    """Validate a calculated field expression without saving it."""
    ds = state.get_dataset(ds_id)
    if ds is None:
        raise HTTPException(404, "Dataset not found")

    errors = calc_engine.validate_expression(req.expression, ds)
    return CalculatedFieldValidateResponse(valid=len(errors) == 0, errors=errors)


@router.get("/calculated-functions")
async def list_supported_functions():
    """List all supported functions for calculated fields."""
    return calc_engine.function_catalog()
