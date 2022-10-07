from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    from_json, 
    col, 
    from_unixtime, 
    to_date, 
    to_timestamp
)
from pyspark.sql.types import (
    StringType,
    StructField,
    StructType,
    BooleanType,
    IntegerType,
    LongType
)

def read_kafka_stream(spark: SparkSession) -> DataFrame:
    # Read the kafka topic [wikistream] 
    df_raw = spark.readStream\
                  .format("kafka")\
                  .option("kafka.bootstrap.servers", "spark-kafka:9092")\
                  .option("subscribe", "wikistream")\
                  .load()

    print(df_raw.isStreaming)
    df_raw.printSchema()

    # The key and value [both binary] received by the kafka topic are converted to string.
    df_raw = df_raw.withColumn("key", df_raw["key"].cast(StringType()))\
                   .withColumn("value", df_raw["value"].cast(StringType()))

    # Event data Schema
    schema = StructType([
        StructField("$schema", StringType(), True),
        StructField("bot", BooleanType(), True),
        StructField("comment", StringType(), True),
        StructField("id", StringType(), True),
        StructField("length", StructType([ 
                                            StructField("new", IntegerType(), True),
                                            StructField("old", IntegerType(), True)
                                        ]), True),
        StructField("meta", StructType([
                                            StructField("domain", StringType(), True),
                                            StructField("dt", StringType(), True),
                                            StructField("id", StringType(), True),
                                            StructField("offset", LongType(), True),
                                            StructField("partition", LongType(), True),
                                            StructField("request_id", StringType(), True),
                                            StructField("stream", StringType(), True),
                                            StructField("topic", StringType(), True),
                                            StructField("uri", StringType(), True),
                                       ]), True),
        StructField("minor", BooleanType(), True),
        StructField("namespace", IntegerType(), True),
        StructField("parsedcomment", StringType(), True),
        StructField("patrolled", BooleanType(), True),
        StructField("revision", StructType([
                                            StructField("new", IntegerType(), True),
                                            StructField("old", IntegerType(), True)
                                        ]), True),
        StructField("server_name", StringType(), True),
        StructField("server_script_path", StringType(), True),
        StructField("server_url", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("title", StringType(), True),
        StructField("type", StringType(), True),
        StructField("user", StringType(), True),
        StructField("wiki", StringType(), True)
    ])

    # Create DataFrame setting schema for event data
    df_wikiStream = df_raw.withColumn("value", from_json("value", schema))
    return df_wikiStream

def performs_some_transformation(df: DataFrame) -> DataFrame:
    """Some transformation like, column renaming, and column conversion 
    unix timestamp to timestamp, 
    """
    df_wikiStream_formatted = df.select(
                                        col("value.$schema").alias("schema"),
                                        "value.bot",
                                        "value.comment",
                                        "value.id",
                                        col("value.length.new").alias("length_new"),
                                        col("value.length.old").alias("length_old"),
                                        "value.minor",
                                        "value.namespace",
                                        "value.parsedcomment",
                                        "value.patrolled",
                                        col("value.revision.new").alias("revesion_new"),
                                        col("value.revision.old").alias("revesion_old"),
                                        "value.server_name",
                                        "value.server_script_path",
                                        "value.server_url",
                                        to_timestamp(from_unixtime(col("value.timestamp"))).alias("change_timestamp"),
                                        to_date(from_unixtime(col("value.timestamp"))).alias("change_timestamp_date"),
                                        "value.title",
                                        "value.type",
                                        "value.user",
                                        "value.wiki",
                                        col("value.meta.domain").alias("meta_domain"),
                                        col("value.meta.dt").alias("meta_dt"),
                                        col("value.meta.id").alias("meta_id"),
                                        col("value.meta.offset").alias("meta_offset"),
                                        col("value.meta.partition").alias("meta_partition"),
                                        col("value.meta.request_id").alias("meta_request_id"),
                                        col("value.meta.stream").alias("meta_stream"),
                                        col("value.meta.topic").alias("meta_topic"),
                                        col("value.meta.uri").alias("meta_uri")
                                    )
                                    
    return df_wikiStream_formatted

def main(spark: SparkSession) -> None:

    data_raw = read_kafka_stream(spark)
    data_formatted = performs_some_transformation(data_raw)
    data_formatted.writeStream\
                        .format("console")\
                        .outputMode("append")\
                        .option("checkpointLocation", "/opt/bitnami/spark/tmp/checkpoint")\
                        .start()\
                        .awaitTermination()
                         

if __name__=="__main__":
    # Create a session
    spark = SparkSession.builder\
            .appName("wikiStream")\
            .master("spark://spark-master:7077")\
            .config("spark.jars", "/opt/bitnami/spark/jars/spark-sql-kafka-0-10_2.12-3.3.0.jar")\
            .config("spark.jars", "/opt/bitnami/spark/jars/spark-streaming-kafka-0-10_2.12-3.3.0.jar")\
            .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    main(spark)

    spark.stop()