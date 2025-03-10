import random
import logging
import requests
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
from flask import Flask, request, jsonify

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Flask App Initialization
app = Flask(__name__)

# Database Configuration
DATABASE_URL = "postgresql://user:password@localhost:5432/mydatabase"  # Update with actual credentials

class Database:
    def __init__(self, num_samples=5, customers_per_sample=10, sampling_method="random", data_percentage=1):
        self.engine = create_engine(DATABASE_URL)
        self.num_samples = num_samples
        self.customers_per_sample = customers_per_sample
        self.sampling_method = sampling_method  # Options: "random", "stratified", "systematic"
        self.data_percentage = data_percentage  # Percentage of the data to retrieve (1% or 2%)
    
    def get_customers(self, include_only_active=True):
        """Fetch customers based on the population selection with configurable percentage using SQL query."""
        percentage_filter = max(1, min(self.data_percentage, 100))  # Ensure valid percentage range
        query = f"""
            SELECT id, name FROM customers
            {"WHERE is_active = TRUE" if include_only_active else ""}
            ORDER BY random()
            LIMIT (SELECT COUNT(*) * {percentage_filter} / 100 FROM customers)
        """
        df = pd.read_sql(query, con=self.engine)
        return df
    
    def select_samples(self, customers_df):
        """Select samples using different statistical methods"""
        if customers_df.empty:
            return []
        
        samples = []
        if self.sampling_method == "random":
            for _ in range(self.num_samples):
                sample_size = min(self.customers_per_sample, len(customers_df))
                sample = customers_df.sample(n=sample_size, replace=False)
                samples.append(sample)
        elif self.sampling_method == "stratified":
            samples = self.stratified_sampling(customers_df)
        elif self.sampling_method == "systematic":
            samples = self.systematic_sampling(customers_df)
        else:
            logging.warning("Unknown sampling method, defaulting to random sampling.")
            return self.select_samples(customers_df)
        
        return samples
    
    def store_results(self, results_data):
        """Store rule engine results in the database using DataFrame and create aggregations"""
        results_df = pd.DataFrame(results_data)
        results_df.to_sql('results', con=self.engine, if_exists='append', index=False)
        
        # Aggregation logic
        total_success = results_df[results_df['rule_engine_result'] == 'Success'].shape[0]
        total_failure = results_df[results_df['rule_engine_result'] == 'Failure'].shape[0]
        total_error = results_df[results_df['rule_engine_result'] == 'API_ERROR'].shape[0]
        
        aggregation_data = {
            "timestamp": datetime.now(),
            "number_of_samples": self.num_samples,
            "number_of_customers": results_df.shape[0],
            "total_success": total_success,
            "total_failure": total_failure,
            "total_error": total_error
        }
        aggregation_df = pd.DataFrame([aggregation_data])
        aggregation_df.to_sql('results_aggregation', con=self.engine, if_exists='append', index=False)
        
        logging.info("Results and aggregation stored successfully.")


class RuleEngine:
    def __init__(self, rule_engine_api_url):
        self.api_url = rule_engine_api_url
    
    def call_rule_engine(self, customer_id, rule_id, caller):
        """Call the external rule engine API for a given customer with additional details"""
        payload = {"customer_id": customer_id, "rule_id": rule_id, "caller": caller}
        try:
            response = requests.post(self.api_url, json=payload)
            if response.status_code == 200:
                return response.json().get("result", "Unknown")
            else:
                logging.error(f"API call failed for customer {customer_id}: {response.status_code}")
                return "API_ERROR"
        except requests.RequestException as e:
            logging.error(f"Error calling API: {e}")
            return "API_ERROR"

@app.route('/run_sampling', methods=['POST'])
def run_sampling():
    data = request.json
    rule_id = data.get("rule_id")
    caller = data.get("caller")
    num_samples = data.get("num_samples", 5)
    customers_per_sample = data.get("customers_per_sample", 10)
    sampling_method = data.get("sampling_method", "random")
    data_percentage = data.get("data_percentage", 1)
    
    database = Database(num_samples, customers_per_sample, sampling_method, data_percentage)
    rule_engine = RuleEngine("http://example.com/rule-engine")  # Replace with actual API
    
    customers_df = database.get_customers(include_only_active=True)
    if customers_df.empty:
        return jsonify({"message": "No customers found!"}), 404
    
    samples = database.select_samples(customers_df)
    results_data = []
    for sample in samples:
        for _, customer in sample.iterrows():
            rule_result = rule_engine.call_rule_engine(customer['id'], rule_id, caller)
            results_data.append({"customer_id": customer['id'], "rule_engine_result": rule_result})
    
    database.store_results(results_data)
    
    return jsonify({"message": "Sampling and rule engine execution completed!"})

if __name__ == '__main__':
    app.run(debug=True)
