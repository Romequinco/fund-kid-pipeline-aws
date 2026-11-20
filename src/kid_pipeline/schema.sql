-- Modelo de datos: un documento (PDF) por SHA-256 y como mucho una extracción por documento.
-- Reprocesar un PDF actualiza su fila en `kid`, no crea otra (D-1.2). Un KID nuevo del mismo ISIN es otro documento.

CREATE TABLE IF NOT EXISTS documentos (
    sha256          CHAR(64) PRIMARY KEY,
    gestora_fuente  TEXT        NOT NULL,
    url_pdf         TEXT        NOT NULL,
    url_ficha       TEXT,
    s3_key          TEXT        NOT NULL UNIQUE,
    bytes           INTEGER,
    descargado_en   TIMESTAMPTZ NOT NULL
);

-- `evidencias`: por campo, el fragmento literal del KID y si aparece en su texto y cuadra con el valor (D-2.4);
-- `evidencias_ok`: todo cuadra (null si no se revisó).
CREATE TABLE IF NOT EXISTS kid (
    documento_sha256             CHAR(64) PRIMARY KEY REFERENCES documentos (sha256),
    isin                         CHAR(12),
    nombre_producto              TEXT,
    nombre_clase                 TEXT,
    gestora                      TEXT,
    fecha_documento              DATE,
    sri                          SMALLINT CHECK (sri BETWEEN 1 AND 7),
    periodo_mantenimiento_anios  NUMERIC(4, 1),
    gastos_corrientes_pct        NUMERIC(6, 3),
    costes_entrada_pct           NUMERIC(6, 3),
    costes_salida_pct            NUMERIC(6, 3),
    modelo                       TEXT        NOT NULL,
    evidencias                   JSONB,
    evidencias_ok                BOOLEAN,
    extraido_en                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS kid_isin ON kid (isin);

-- El KID vigente de cada clase: el de fecha más reciente (o el último extraído si no hay fecha).
CREATE OR REPLACE VIEW kid_vigente AS
SELECT DISTINCT ON (k.isin) k.*, d.gestora_fuente, d.url_pdf, d.descargado_en
FROM kid k
JOIN documentos d ON d.sha256 = k.documento_sha256
WHERE k.isin IS NOT NULL
ORDER BY k.isin, k.fecha_documento DESC NULLS LAST, k.extraido_en DESC;
