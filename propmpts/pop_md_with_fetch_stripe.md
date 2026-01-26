# Populating Market Data

## Data Example
Example of one element of the list returned by the "https://api.invertironline.com/api/v2/bCBA/Titulos/{symbol}/Opciones" endpoint.

```json
{
    "cotizacion": {
        "ultimoPrecio": 5100,
        "variacion": 0,
        "apertura": 0,
        "maximo": 0,
        "minimo": 0,
        "fechaHora": "0001-01-01T00:00:00",
        "tendencia": "sube",
        "cierreAnterior": 0,
        "montoOperado": 0,
        "volumenNominal": 0,
        "precioPromedio": 0,
        "moneda": 0,
        "precioAjuste": 0,
        "interesesAbiertos": 0,
        "puntas": null,
        "cantidadOperaciones": 0,
        "descripcionTitulo": null,
        "plazo": null,
        "laminaMinima": 0,
        "lote": 0
    },
    "simboloSubyacente": "GGAL",
    "fechaVencimiento": "2025-12-19T00:00:00",
    "tipoOpcion": "Call",
    "simbolo": "GFGC26549D",
    "descripcion": "Call GGAL 2,654.90 Vencimiento: 19/12/2025",
    "pais": "argentina",
    "mercado": "bcba",
    "tipo": "OPCIONES",
    "plazo": "t1",
    "moneda": "peso_Argentino"
}
```

## Data Population Strategy

This section explains how to extract information from the API response (JSON) to populate the tables defined in `DatabaseDesign.md`.

### 1. Populating `options_contracts`
This table stores static data. We extract this from the root level of the JSON object.

| Database Column | JSON Field | Transformation / Notes |
| :--- | :--- | :--- |
| `symbol` | `simbolo` | Direct mapping. |
| `underlying_symbol` | `simboloSubyacente` | Direct mapping. |
| `type` | `tipoOpcion` | Direct mapping ("Call" or "Put"). |
| `expiration_date` | `fechaVencimiento` | Direct mapping (ISO 8601 format). |
| `strike` | Derived from `descripcion` | **Logic**: Split the description string by spaces. Iterate through each part, removing commas. The first part that is a valid number is identified as the strike price. <br> Example: "Call GGAL 2,654.90 Vencimiento..." -> Splits to ["Call", "GGAL", "2,654.90", ...] -> "2,654.90" becomes 2654.90. |
| `description` | `descripcion` | Direct mapping. |

### 2. Populating `market_prices`
This table stores dynamic price data. We extract this primarily from the `cotizacion` nested object.

| Database Column | JSON Field | Transformation / Notes |
| :--- | :--- | :--- |
| `contract_symbol` | `simbolo` | Direct mapping (Foreign Key). |
| `price` | `cotizacion.ultimoPrecio` | Direct mapping. |
| `broker_timestamp` | `cotizacion.fechaHora` | Direct mapping. **Note**: If `fechaHora` is "0001-01-01...", use None. |
| `system_timestamp` | System Time | Use the current system time when the data is fetched/inserted. |
| `volume` | `cotizacion.volumenNominal` | Direct mapping. |