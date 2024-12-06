import json
from pyspark.sql import DataFrame
from rapidfuzz import process
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


def rename_columns_with_similarity(
    df: DataFrame, schema_fields: list[str], parquet_name: str, threshold: float = 0.8
) -> DataFrame:
    """
    Renombra las columnas de un DataFrame usando similitud con los nombres del esquema Avro.
    Incluye validación para nombres similares y permite interacción manual.

    Parámetros
    ----------
    df : pyspark.sql.DataFrame
        DataFrame de Spark cuyas columnas deben ser renombradas.
    schema_fields : list
        Lista de nombres de columnas del esquema Avro.
    parquet_name : str
        Nombre del archivo parquet usado como referencia.
    threshold : float
        Umbral mínimo de similitud para considerar una coincidencia (entre 0 y 1).

    Retorna
    -------
    pyspark.sql.DataFrame
        DataFrame con columnas renombradas.
    """
    current_columns = df.columns
    unmatched_columns = []
    column_mapping = {}

    for schema_field in schema_fields:
        # Buscar coincidencias exactas (case-insensitive)
        exact_match = next(
            (col for col in current_columns if col.lower() == schema_field.lower()),
            None,
        )

        if exact_match:
            column_mapping[exact_match] = schema_field
        else:
            # Si no hay coincidencia exacta, buscar las mejores aproximaciones
            matches = process.extract(
                schema_field, current_columns, limit=3, score_cutoff=threshold * 100
            )

            if len(matches) == 1:
                # Si solo hay una coincidencia clara, mapearla automáticamente
                matched_column, score, _ = matches[0]
                column_mapping[matched_column] = schema_field
            elif len(matches) > 1:
                # Si hay múltiples coincidencias, pedir al usuario que seleccione
                print(
                    f"Advertencia: Múltiples coincidencias para '{schema_field}' en '{parquet_name}':"
                )
                for i, match in enumerate(matches, start=1):
                    print(f"  {i}. {match[0]} (score: {match[1]:.2f})")

                # Solicitar al usuario que elija una opción
                while True:
                    try:
                        choice = int(
                            input(
                                f"Seleccione el número correspondiente para mapear '{schema_field}': "
                            )
                        )
                        if 1 <= choice <= len(matches):
                            matched_column, score, _ = matches[choice - 1]
                            column_mapping[matched_column] = schema_field
                            print(
                                f"Seleccionado: '{matched_column}' para mapear a '{schema_field}'"
                            )
                            break
                        else:
                            print("Opción fuera de rango. Intente de nuevo.")
                    except ValueError:
                        print("Entrada inválida. Por favor, ingrese un número.")
            else:
                # No se encontraron coincidencias
                unmatched_columns.append(schema_field)

    if unmatched_columns:
        raise ValueError(
            f"No se pudo mapear las siguientes columnas del esquema '{parquet_name}': {unmatched_columns}"
        )

    for original, target in column_mapping.items():
        print(f"Renombrando '{original}' a '{target}' en {parquet_name}")

    return df.select(
        [df[col].alias(column_mapping.get(col, col)) for col in current_columns]
    )


def main():
    session = SparkSessionManager()
    avro_session = session.create_avro_session()

    schema_path = rf"schemas\schema_avro_cartera.avsc"

    # Cargar campos desde el esquema Avro
    creditos_fields = load_avro_fields(schema_path, "creditos")
    movimientos_fields = load_avro_fields(schema_path, "movimientos")
    demograficos_fields = load_avro_fields(schema_path, "demograficos")

    # Rutas de archivos Parquet
    path_creditos = "fuentes/creditos.parquet"
    path_movimientos = "fuentes/movimientos.parquet"
    path_demograficos = "fuentes/demograficos.parquet"

    # Leer DataFrames
    df_creditos = avro_session.read.parquet(path_creditos)
    df_movimientos = avro_session.read.parquet(path_movimientos)
    df_demograficos = avro_session.read.parquet(path_demograficos)

    # Renombrar columnas con similitud
    df_creditos = rename_columns_with_similarity(
        df_creditos, creditos_fields, "creditos"
    )
    df_movimientos = rename_columns_with_similarity(
        df_movimientos, movimientos_fields, "movimientos"
    )
    df_demograficos = rename_columns_with_similarity(
        df_demograficos, demograficos_fields, "demograficos"
    )

    # Guardar DataFrames renombrados
    df_creditos.write.mode("overwrite").parquet("output/creditos_renamed.parquet")
    df_movimientos.write.mode("overwrite").parquet("output/movimientos_renamed.parquet")
    df_demograficos.write.mode("overwrite").parquet(
        "output/demograficos_renamed.parquet"
    )


if __name__ == "__main__":
    main()
