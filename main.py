import json
import pyspark

from spark.session import SparkSessionManager


def load_avro_fields(schema_path: str, field_name: str) -> list[str]:
    """
    Carga los campos de un objeto específico en un esquema Avro.

    Parámetros
    ----------
    schema_path : str
        Ruta al archivo del esquema Avro.
    field_name : str
        Nombre del objeto dentro del esquema Avro cuyos campos deben extraerse.

    Retorna
    -------
    list
        Lista de nombres de columnas dentro del objeto especificado en el esquema Avro.
    """
    with open(schema_path, "r") as avro_file:
        schema_avro = json.load(avro_file)

    for field in schema_avro.get("fields", []):
        if field["name"] == field_name:
            return [f["name"] for f in field["type"]["items"]["fields"]]

    raise ValueError(f"El campo '{field_name}' no se encontró en el esquema Avro.")


def rename_columns(
    df: pyspark.sql.DataFrame, schema_fields: list[str], parquet_name: str
) -> pyspark.sql.DataFrame:
    """
    Renombra las columnas de un DataFrame para que coincidan con el esquema Avro.

    Parámetros
    ----------
    df : pyspark.sql.DataFrame
        DataFrame de Spark cuyas columnas deben ser renombradas.
    schema_fields : list
        Lista de nombres de columnas del esquema Avro.
    parquet_name : str
        Nombre del archivo parquet usado como referencia.

    Retorna
    -------
    pyspark.sql.DataFrame
        DataFrame con columnas renombradas.
    """
    current_columns = df.columns
    column_mapping = {
        col: schema_field for col, schema_field in zip(current_columns, schema_fields)
    }

    if len(current_columns) != len(schema_fields):
        print(
            f"Advertencia: El número de columnas en {parquet_name} no coincide con el esquema Avro."
        )

    for original, target in column_mapping.items():
        print(f"Renombrando {original} a {target} en {parquet_name}")

    return df.select(
        [df[col].alias(column_mapping.get(col, col)) for col in current_columns]
    )


def main():
    session = SparkSessionManager()
    avro_session = session.create_avro_session()

    schema_path = rf"schemas\schema_avro_cartera.avsc"

    creditos_fields = load_avro_fields(schema_path, "creditos")
    movimientos_fields = load_avro_fields(schema_path, "movimientos")
    demograficos_fields = load_avro_fields(schema_path, "demograficos")

    path_creditos = "fuentes/creditos.parquet"
    path_movimientos = "fuentes/movimientos.parquet"
    path_demograficos = "fuentes/demograficos.parquet"

    df_creditos = avro_session.read.parquet(path_creditos)
    df_movimientos = avro_session.read.parquet(path_movimientos)
    df_demograficos = avro_session.read.parquet(path_demograficos)

    df_creditos = rename_columns(df_creditos, creditos_fields, "creditos")
    df_movimientos = rename_columns(df_movimientos, movimientos_fields, "movimientos")
    df_demograficos = rename_columns(
        df_demograficos, demograficos_fields, "demograficos"
    )

    df_creditos.write.mode("overwrite").parquet("output/creditos_renamed.parquet")
    df_movimientos.write.mode("overwrite").parquet("output/movimientos_renamed.parquet")
    df_demograficos.write.mode("overwrite").parquet(
        "output/demograficos_renamed.parquet"
    )


if __name__ == "__main__":
    main()
