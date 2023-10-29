import simpy
import random

class Buffet:
    def __init__(self, env, num_entrances, num_tables):
        self.env = env
        self.entrances = simpy.Resource(env, num_entrances)
        self.tables = simpy.Resource(env, num_tables)
    
    def serve_food(self, customer):
        yield self.env.timeout(random.expovariate(1))  # Thời gian phục vụ khách hàng

    def enter_buffet(self, customer):
        yield self.env.timeout(random.expovariate(0.5))  # Thời gian khách hàng đến buffet
        with self.entrances.request() as request:
            yield request
            yield self.env.process(self.serve_food(customer))
            with self.tables.request() as table_request:
                yield table_request
                yield self.env.timeout(random.expovariate(0.5))  # Thời gian khách hàng ăn

def customer(env, buffet):
    customer_id = 1
    while True:
        print(f"Customer {customer_id} arrives at time {env.now}")
        env.process(buffet.enter_buffet(customer_id))
        customer_id += 1
        yield env.timeout(random.expovariate(0.2))  # Thời gian giữa việc đến của các khách hàng

env = simpy.Environment()
buffet = Buffet(env, num_entrances=2, num_tables=5)
env.process(customer(env, buffet))
env.run(until=20)  # Thời gian chạy mô phỏng