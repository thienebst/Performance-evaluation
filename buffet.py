import simpy
import random

class Customer:
    def __init__(self, name):
        self.name = name
        self.history = []

    def add_to_history(self, event):
        self.history.append(event)

class Queue:
    def __init__(self, env, name, capacity):
        self.env = env
        self.name = name
        self.queue = simpy.Store(env, capacity=capacity)

    def enqueue(self, customer):
        yield self.queue.put(customer)

    def dequeue(self):
        return self.queue.get()

class Server:
    def __init__(self, env, name, service_time):
        self.env = env
        self.name = name
        self.service_time = service_time
        self.busy = False

    def serve(self, customer): 
        yield self.env.timeout(self.service_time)
        customer.add_to_history(f"{self.env.now} - served by {self.name}")

class System:
    def __init__(self, env, num_customers, arrival_rate, service_times, queue_capacities, total_time):
        self.env = env
        self.total_time = total_time
        self.num_customers = num_customers
        self.customers = []
        self.arrival_rate = arrival_rate
        self.queue_capacities = queue_capacities
        # Create queues
        self.waiting_queue = Queue(env, "Waiting Queue", capacity=1)
        self.order_queues = [Queue(env, f"Order Queue {i}", capacity=2) for i in range(2)]
        self.stall_queues = [Queue(env, f"Stall Queue {i}", capacity=2) for i in range(3)]
        self.payment_queue = Queue(env, "Payment Queue", capacity=1)

        # Create servers
        self.waiting_server = Server(env, "Waiting Server", service_times[0])
        self.order_servers = [Server(env, f"Order Server {i}", service_times[i+1]) for i in range(4)]
        self.stall_servers = [Server(env, f"Stall Server {i}", service_times[i+5]) for i in range(6)]
        self.payment_server = Server(env, "Payment Server", service_times[11])

    def customer_arrival_process(self):
        for i in range(self.num_customers):
            customer = Customer(f"Customer-{i}")
            self.customers.append(customer)
            yield self.env.process(self.waiting_queue.enqueue(customer))
            yield self.env.timeout(random.expovariate(self.arrival_rate))
    
    def order_process(self, queue, servers):
         while True:
            for i in range(2):
              customer = yield queue.dequeue() 
              yield self.env.process(servers[i].serve(customer)) 
              yield self.env.process(self.stall_queues[random.choice([0, 1, 2])].enqueue(customer))
    def stall_process(self, queue, servers):
         while True:
            for i in range(2):
              customer = yield queue.dequeue() 
              yield self.env.process(servers[i].serve(customer))
              decision = random.choice(["payment", "order", "other_stall"])
                
              if decision == "payment":
                    yield self.env.process(self.payment_queue.enqueue(customer))
              elif decision == "order":
                    yield self.env.process(self.order_queues[random.choice([0, 1])].enqueue(customer))
              else:  # "other_stall"
                    other_stall_queue = list(self.stall_queues)
                    other_stall_queue.remove(queue)
                    yield self.env.process(other_stall_queue[random.choice([0, 1])].enqueue(customer))

    def payment_process(self):
        while True:
            customer = yield self.payment_queue.dequeue() 
            yield self.env.process(self.payment_server.serve(customer))          
    def waiting_process(self):
        while True:
            customer = yield self.waiting_queue.dequeue() 
            yield self.env.process(self.waiting_server.serve(customer)) 
            yield self.env.process(self.order_queues[random.choice([0, 1])].enqueue(customer))   
    def run(self):
        self.env.process(self.customer_arrival_process())
        self.env.process(self.waiting_process())
        for i in range(2):
          self.env.process(self.order_process(self.order_queues[i],self.order_servers[ i * 2 : i * 2 + 2])) 
        for i in range(3):
          self.env.process(self.stall_process(self.stall_queues[i], self.stall_servers[ i * 2 : i * 2 + 2]))
        
        self.env.process(self.payment_process())
        self.env.run(until=self.env.now + self.total_time)  # Adjust the simulation time as needed
        # Print the customer's history 
        for customer in self.customers: 
            print(f"# {customer.name} History:")
            for event in customer.history:
              print(event)

def main():
    env = simpy.Environment()
    total_time = 1000
    num_customers = 10
    arrival_rate = 0.4
    service_times = [1, 3, 4, 3, 5, 4, 3, 4, 4, 3, 5, 1]  # 1 Waiting, 4 Order, 6 Stall, 1 Payment
    queue_capacities = [5, 3, 3, 3, 3, 5]  # 1 Waiting, 2 Order, 3 Stall, 1 Payment

    system = System(env, num_customers, arrival_rate, service_times, queue_capacities, total_time)
    system.run()

if __name__ == "__main__":
    main()

 