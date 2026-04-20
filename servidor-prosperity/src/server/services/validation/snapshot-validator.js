import { snapshotLegacyContract } from "../../domain/contracts/snapshot-legacy.js";

function hasValue(value) {
  if (Array.isArray(value)) {
    return value.length > 0;
  }

  return value !== undefined && value !== null && value !== "";
}

export function validateLegacySnapshot(payload = {}) {
  const missingFields = snapshotLegacyContract.requiredFields.filter(
    (fieldName) => !hasValue(payload[fieldName]),
  );

  const issues = [...missingFields.map((fieldName) => `Falta el campo requerido "${fieldName}".`)];

  if (payload.price !== undefined && Number.isNaN(Number(payload.price))) {
    issues.push('El campo "price" no es numerico.');
  }

  if (
    payload.open_positions_count !== undefined &&
    Number.isNaN(Number(payload.open_positions_count))
  ) {
    issues.push('El campo "open_positions_count" no es numerico.');
  }

  return {
    contract: snapshotLegacyContract.name,
    is_valid: issues.length === 0,
    issues,
    missing_fields: missingFields,
    checked_at: new Date().toISOString(),
  };
}
