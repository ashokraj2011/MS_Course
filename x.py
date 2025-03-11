import random
import logging
import requests
import pandas as pd
import uuid
import asyncio
import aiohttp
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

class RuleEngine:
    def __init__(self, rule_engine_api_url):
        self.api_url = rule_engine_api_url
    
    async def call_rule_engine(self, session, customer_id, rule_id, caller):
        """Call the external rule engine API asynchronously for a given customer and rule ID"""
        payload = {"customer_id": customer_id, "rule_id": rule_id, "caller": caller}
        try:
            async with session.post(self.api_url, json=payload) as response:
                if response.status == 200:
                    return rule_id, await response.json()
                else:
                    logging.error(f"API call failed for customer {customer_id} with rule {rule_id}: {response.status}")
                    return rule_id, {"result": "API_ERROR"}
        except Exception as e:
            logging.error(f"Error calling API for rule {rule_id}: {e}")
            return rule_id, {"result": "API_ERROR"}

async def process_customers(rule_engine, customers, rule_ids, caller):
    """Asynchronously process multiple customers and call the rule engine API in parallel"""
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [
            rule_engine.call_rule_engine(session, customer['id'], rule_id, caller)
            for customer in customers for rule_id in rule_ids
        ]
        responses = await asyncio.gather(*tasks)
        for rule_id, response in responses:
            results.append({"customer_id": response.get("customer_id"), "rule_id": rule_id, "rule_engine_result": response.get("result", "Unknown")})
    return results

@app.route('/run_sampling', methods=['POST'])
def run_sampling():
    run_id = uuid.uuid4().hex  # Generate a unique run ID
    data = request.json
    rule_ids = data.get("rule_ids", [])  # Expecting a list of rule IDs
    caller = data.get("caller")
    num_samples = data.get("num_samples", 5)
    customers_per_sample = data.get("customers_per_sample", 10)
    sampling_method = data.get("sampling_method", "random")
    data_percentage = data.get("data_percentage", 1)
    
    if not rule_ids:
        return jsonify({"message": "No rule IDs provided!"}), 400
    
    database = Database(num_samples, customers_per_sample, sampling_method, data_percentage)
    rule_engine = RuleEngine("http://example.com/rule-engine")  # Replace with actual API
    
    customers_df = database.get_customers(include_only_active=True)
    if customers_df.empty:
        return jsonify({"message": "No customers found!"}), 404
    
    samples = database.select_samples(customers_df)
    results_data = []
    for sample in samples:
        results = asyncio.run(process_customers(rule_engine, sample.to_dict(orient="records"), rule_ids, caller))
        results_data.extend(results)
    
    database.store_results(results_data, run_id, caller)
    
    return jsonify({"message": "Sampling and rule engine execution completed!", "run_id": run_id})

if __name__ == '__main__':
    app.run(debug=True)
