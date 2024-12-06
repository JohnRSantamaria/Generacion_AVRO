from pyspark.sql import SparkSession as PySparkSession


class SparkSessionManager:
    """
    Clase de utilidad para crear y gestionar sesiones de Spark con configuraciones predefinidas.

    Métodos
    -------
    create_local_session() -> pyspark.sql.SparkSession:
        Crea una sesión de Spark para procesamiento local con configuraciones predeterminadas.

    create_avro_session() -> pyspark.sql.SparkSession:
        Crea una sesión de Spark configurada para procesar archivos grandes,
        con soporte para el formato Avro y mayor asignación de memoria.
    """

    @staticmethod
    def create_local_session() -> PySparkSession:
        """
        Crea una sesión de Spark para procesamiento local.

        Retorna
        -------
        pyspark.sql.SparkSession
            Una sesión de Spark con el nombre de la aplicación "LocalProcessor"
            y el maestro configurado como "local[*]".
        """
        local_session = (
            PySparkSession.builder.appName("LocalProcessor")
            .master("local[*]")
            .getOrCreate()
        )
        return local_session

    @staticmethod
    def create_avro_session() -> PySparkSession:
        """
        Crea una sesión de Spark configurada para procesar archivos grandes con soporte para Avro.

        Esta sesión está configurada con:
        - Nombre de la aplicación: "AvroFileProcessor"
        - Maestro: local[*]
        - Memoria para el driver: 8 GB
        - Memoria para el ejecutor: 8 GB
        - Paquete de Spark Avro: org.apache.spark:spark-avro_2.12:3.5.0

        Retorna
        -------
        pyspark.sql.SparkSession
            Una sesión de Spark configurada con las configuraciones anteriores.
        """
        avro_session = (
            PySparkSession.builder.appName("AvroFileProcessor")
            .master("local[*]")
            .config("spark.driver.memory", "8g")
            .config("spark.executor.memory", "8g")
            .config("spark.jars.packages", "org.apache.spark:spark-avro_2.12:3.5.0")
            .getOrCreate()
        )
        return avro_session
