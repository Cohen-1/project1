from locust import HttpUser, task, between
import random 

class Shopper(HttpUser):
    wait_time = between(1,3)


    @task(3)
    def browse_products(self):
        self.client.get("/api/products?page=" + str(random.randint(1,5)))

    
    @task(2)
    def view_product(self):
        pid = random.randint(1001, 1100)
        self.client.get(f"api/products/{pid}")

    @task(2)
    def add_to_cart(self):
        pid = random.randint(1001, 1100)
        self.client.post("api/cart", json={"product_id": pid, "quantity": 1})

    @task(1)
    def checkout(self):
        self.client.post("/api/checkout/shipping", json={"address": "123 Langihan"})
        self.client.post("/api/checkout/payment", json={"payment_method": "card", "token": "tok_test"})
        self.client.post("/api/checkout/place_order", json={"agree_terms": True})


