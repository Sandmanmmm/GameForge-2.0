# Audit Data Analytics with Apache Spark
# File: audit/analytics/audit_analytics.py

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans
from pyspark.ml.stat import Correlation
import json
from datetime import datetime, timedelta

class AuditAnalytics:
    def __init__(self):
        self.spark = SparkSession.builder \
            .appName("GameForge-Audit-Analytics") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .getOrCreate()

        self.spark.sparkContext.setLogLevel("WARN")

    def load_audit_data(self, days_back=7):
        """Load audit data from Elasticsearch for analysis"""

        # Define schema for audit data
        audit_schema = StructType([
            StructField("@timestamp", TimestampType(), True),
            StructField("user_id", StringType(), True),
            StructField("session_id", StringType(), True),
            StructField("action", StringType(), True),
            StructField("resource", StringType(), True),
            StructField("ip_address", StringType(), True),
            StructField("success", BooleanType(), True),
            StructField("duration_ms", LongType(), True),
            StructField("service", StringType(), True),
            StructField("severity", StringType(), True),
            StructField("compliance_violation", BooleanType(), True),
            StructField("security_event", BooleanType(), True)
        ])

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Load data from Elasticsearch (simulated for demo)
        # In production, use elasticsearch-hadoop connector
        df = self.spark.read \
            .format("org.elasticsearch.spark.sql") \
            .option("es.nodes", "elasticsearch-audit") \
            .option("es.port", "9200") \
            .option("es.nodes.wan.only", "true") \
            .option("es.resource", f"gameforge-audit-*") \
            .option("es.query", f'{{"range": {{"@timestamp": {{"gte": "{start_date.isoformat()}", "lte": "{end_date.isoformat()}"}}}}}}') \
            .load()

        return df

    def detect_anomalous_user_behavior(self, audit_df):
        """Detect anomalous user behavior patterns"""

        # User activity aggregation
        user_activity = audit_df.groupBy("user_id") \
            .agg(
                count("*").alias("total_actions"),
                countDistinct("action").alias("unique_actions"),
                countDistinct("resource").alias("unique_resources"),
                countDistinct("ip_address").alias("unique_ips"),
                avg("duration_ms").alias("avg_duration"),
                sum(when(col("success") == False, 1).otherwise(0)).alias("failed_actions"),
                sum(when(col("security_event") == True, 1).otherwise(0)).alias("security_events"),
                sum(when(col("compliance_violation") == True, 1).otherwise(0)).alias("compliance_violations")
            )

        # Feature engineering for anomaly detection
        assembler = VectorAssembler(
            inputCols=["total_actions", "unique_actions", "unique_resources", 
                      "unique_ips", "avg_duration", "failed_actions", 
                      "security_events", "compliance_violations"],
            outputCol="features"
        )

        feature_df = assembler.transform(user_activity)

        # K-means clustering for anomaly detection
        kmeans = KMeans(k=5, seed=42, featuresCol="features", predictionCol="cluster")
        model = kmeans.fit(feature_df)
        predictions = model.transform(feature_df)

        # Identify outliers (users in small clusters)
        cluster_counts = predictions.groupBy("cluster").count()
        small_clusters = cluster_counts.filter(col("count") < 5).select("cluster").rdd.flatMap(lambda x: x).collect()

        anomalous_users = predictions.filter(col("cluster").isin(small_clusters))

        return anomalous_users.select("user_id", "total_actions", "unique_ips", 
                                    "failed_actions", "security_events", "cluster")

    def analyze_access_patterns(self, audit_df):
        """Analyze resource access patterns and permissions"""

        # Resource access frequency
        resource_access = audit_df.groupBy("resource", "action") \
            .agg(
                count("*").alias("access_count"),
                countDistinct("user_id").alias("unique_users"),
                avg("duration_ms").alias("avg_duration"),
                sum(when(col("success") == False, 1).otherwise(0)).alias("failed_attempts")
            ) \
            .orderBy(desc("access_count"))

        # Time-based access patterns
        time_patterns = audit_df \
            .withColumn("hour", hour(col("@timestamp"))) \
            .withColumn("day_of_week", dayofweek(col("@timestamp"))) \
            .groupBy("hour", "day_of_week") \
            .agg(
                count("*").alias("activity_count"),
                sum(when(col("security_event") == True, 1).otherwise(0)).alias("security_events")
            )

        return resource_access, time_patterns

    def compliance_analysis(self, audit_df):
        """Analyze compliance violations and generate reports"""

        # Compliance violations by type
        violations = audit_df.filter(col("compliance_violation") == True) \
            .groupBy("action", "resource", "severity") \
            .agg(
                count("*").alias("violation_count"),
                countDistinct("user_id").alias("affected_users"),
                collect_set("user_id").alias("user_list")
            ) \
            .orderBy(desc("violation_count"))

        # Security events analysis
        security_events = audit_df.filter(col("security_event") == True) \
            .groupBy("action", "service") \
            .agg(
                count("*").alias("event_count"),
                countDistinct("user_id").alias("affected_users"),
                countDistinct("ip_address").alias("source_ips")
            ) \
            .orderBy(desc("event_count"))

        # Failed authentication attempts
        failed_auth = audit_df \
            .filter((col("action") == "authentication") & (col("success") == False)) \
            .groupBy("ip_address", "user_id") \
            .agg(count("*").alias("failed_attempts")) \
            .filter(col("failed_attempts") > 5) \
            .orderBy(desc("failed_attempts"))

        return violations, security_events, failed_auth

    def generate_audit_report(self, days_back=7):
        """Generate comprehensive audit analytics report"""

        print(f"Generating audit analytics report for last {days_back} days...")

        # Load audit data
        audit_df = self.load_audit_data(days_back)

        # Cache the dataframe for multiple operations
        audit_df.cache()

        print(f"Loaded {audit_df.count()} audit records")

        # Anomaly detection
        anomalous_users = self.detect_anomalous_user_behavior(audit_df)
        print(f"Detected {anomalous_users.count()} anomalous users")

        # Access pattern analysis
        resource_access, time_patterns = self.analyze_access_patterns(audit_df)

        # Compliance analysis
        violations, security_events, failed_auth = self.compliance_analysis(audit_df)

        # Generate summary statistics
        total_events = audit_df.count()
        unique_users = audit_df.select("user_id").distinct().count()
        security_event_count = audit_df.filter(col("security_event") == True).count()
        compliance_violation_count = audit_df.filter(col("compliance_violation") == True).count()

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "analysis_period_days": days_back,
            "summary": {
                "total_audit_events": total_events,
                "unique_users": unique_users,
                "security_events": security_event_count,
                "compliance_violations": compliance_violation_count,
                "anomalous_users": anomalous_users.count()
            },
            "top_accessed_resources": resource_access.limit(10).collect(),
            "security_incidents": security_events.limit(10).collect(),
            "compliance_violations": violations.limit(10).collect(),
            "failed_authentication_sources": failed_auth.limit(10).collect(),
            "anomalous_user_behavior": anomalous_users.collect()
        }

        # Save report
        with open(f"/opt/bitnami/spark/analytics/audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(report, f, indent=2, default=str)

        return report

    def real_time_anomaly_detection(self):
        """Real-time anomaly detection using Spark Streaming"""

        from pyspark.sql import functions as F
        from pyspark.sql.types import *

        # Define schema for Kafka messages
        kafka_schema = StructType([
            StructField("timestamp", TimestampType(), True),
            StructField("user_id", StringType(), True),
            StructField("action", StringType(), True),
            StructField("resource", StringType(), True),
            StructField("ip_address", StringType(), True),
            StructField("success", BooleanType(), True)
        ])

        # Read from Kafka
        kafka_df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "kafka-audit:29092") \
            .option("subscribe", "audit-events") \
            .option("startingOffsets", "latest") \
            .load()

        # Parse JSON messages
        parsed_df = kafka_df.select(
            from_json(col("value").cast("string"), kafka_schema).alias("data")
        ).select("data.*")

        # Real-time aggregations for anomaly detection
        anomaly_detection = parsed_df \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(
                window(col("timestamp"), "5 minutes"),
                col("user_id")
            ) \
            .agg(
                count("*").alias("action_count"),
                countDistinct("action").alias("unique_actions"),
                countDistinct("ip_address").alias("unique_ips"),
                sum(when(col("success") == False, 1).otherwise(0)).alias("failed_actions")
            ) \
            .filter(
                (col("action_count") > 100) |  # Too many actions
                (col("unique_ips") > 5) |      # Multiple IPs
                (col("failed_actions") > 10)   # Many failures
            )

        # Output anomalies to console and Kafka
        query = anomaly_detection \
            .writeStream \
            .outputMode("append") \
            .format("console") \
            .option("truncate", False) \
            .trigger(processingTime="30 seconds") \
            .start()

        return query

if __name__ == "__main__":
    analytics = AuditAnalytics()

    # Generate daily report
    report = analytics.generate_audit_report(days_back=1)
    print(json.dumps(report["summary"], indent=2))

    # Start real-time anomaly detection
    # streaming_query = analytics.real_time_anomaly_detection()
    # streaming_query.awaitTermination()
