import simpy
import random


class Customer:
    def __init__(self, name):
        self.name = name
        self.waiting_time = []
        self.service_time = []

    def add_to_waiting_time(self, event, time):
        self.waiting_time.append((time, event))

    def add_to_service_time(self, event, time):
        self.service_time.append((time, event))


class Queue:
    def __init__(self, env, name, capacity):
        self.env = env
        self.name = name
        self.queue = simpy.Store(env, capacity=capacity)

    def enqueue(self, customer):
        start_time = self.env.now
        customer.add_to_waiting_time(f"enqueue {self.name}", start_time)
        yield self.queue.put(customer)

    def dequeue(self):
        customer = yield self.queue.get()
        end_time = self.env.now
        customer.add_to_waiting_time(f"dequeue {self.name}", end_time)
        return customer


class Server:
    def __init__(self, env, name, service_time):
        self.env = env
        self.name = name
        self.service_time = service_time
        self.busy = False

    def serve(self, customer):
        start_time = self.env.now  # Record the start time
        yield self.env.timeout(self.service_time)
        end_time = self.env.now  # Record the end time
        customer.add_to_service_time(f"served by {self.name}", start_time)
        customer.add_to_service_time(f"completed service by {self.name}", end_time)


class System:
    def __init__(
        self,
        env,
        num_customers,
        arrival_rate,
        service_times,
        queue_capacities,
        total_time,
    ):
        self.env = env
        self.total_time = total_time
        self.num_customers = num_customers
        self.customers = []
        self.arrival_rate = arrival_rate
        self.queue_capacities = queue_capacities
        # Create queues
        self.waiting_queue = Queue(env, "Waiting Queue", queue_capacities[0])
        self.order_queues = [
            Queue(env, f"Order Queue {i}", queue_capacities[1 + i]) for i in range(2)
        ]
        self.stall_queues = [
            Queue(env, f"Stall Queue {i}", queue_capacities[3 + i]) for i in range(3)
        ]
        self.payment_queue = Queue(env, "Payment Queue", queue_capacities[-1])

        # Create servers
        self.waiting_server = Server(env, "Waiting Server", service_times[0])
        self.order_servers = [
            Server(env, f"Order Server {i}", service_times[i + 1]) for i in range(4)
        ]
        self.stall_servers = [
            Server(env, f"Stall Server {i}", service_times[i + 5]) for i in range(6)
        ]
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
                customer = yield self.env.process(queue.dequeue())
                yield self.env.process(servers[i].serve(customer))
                yield self.env.process(
                    self.stall_queues[random.choice([0, 1, 2])].enqueue(customer)
                )

    def stall_process(self, queue, servers):
        while True:
            for i in range(2):
                customer = yield self.env.process(queue.dequeue())
                yield self.env.process(servers[i].serve(customer))
                if random.choice([True, False]):
                    yield self.env.process(self.payment_queue.enqueue(customer))
                else:
                    if random.choice([True, False]):
                        yield self.env.process(
                            self.order_queues[random.choice([0, 1])].enqueue(customer)
                        )
                    else:
                        other_stall_queue = list(self.stall_queues)
                        other_stall_queue.remove(queue)
                        yield self.env.process(
                            other_stall_queue[random.choice([0, 1])].enqueue(customer)
                        )

    def payment_process(self):
        while True:
            customer = yield self.env.process(self.payment_queue.dequeue())
            yield self.env.process(self.payment_server.serve(customer))

    def waiting_process(self):
        while True:
            customer = yield self.env.process(self.waiting_queue.dequeue())

            yield self.env.process(self.waiting_server.serve(customer))
            yield self.env.process(
                self.order_queues[random.choice([0, 1])].enqueue(customer)
            )

    def run(self):
        self.env.process(self.customer_arrival_process())
        self.env.process(self.waiting_process())
        for i in range(2):
            self.env.process(
                self.order_process(
                    self.order_queues[i], self.order_servers[i * 2 : i * 2 + 2]
                )
            )
        for i in range(3):
            self.env.process(
                self.stall_process(
                    self.stall_queues[i], self.stall_servers[i * 2 : i * 2 + 2]
                )
            )

        self.env.process(self.payment_process())
        self.env.run(
            until=self.env.now + self.total_time
        )  # Adjust the simulation time as needed
        # Print the customer's history
        for customer in self.customers:
            print(f"# {customer.name} History:")
            for event in customer.service_time:
                print(event)
            for event in customer.waiting_time:
                print(event)


def calculate_system_metrics(system):
    customer_finished = [
        customer
        for customer in system.customers
        if len(customer.service_time) > 0
        and customer.service_time[-1][1] == "completed service by Payment Server"
    ]

    # Total Service Time
    total_service_time = 0
    for customer in customer_finished:
        for i in range(0, len(customer.service_time), 2):
            total_service_time += (
                customer.service_time[i + 1][0] - customer.service_time[i][0]
            )
    # Server Utilization Rate
    server_utilization_rate = total_service_time / system.total_time
    # Total Waiting Time
    total_waiting_time = 0
    for customer in customer_finished:
        for i in range(0, len(customer.waiting_time), 2):
            total_waiting_time += (
                customer.waiting_time[i + 1][0] - customer.waiting_time[i][0]
            )

    # Average
    average_waiting_time = total_waiting_time / len(customer_finished)
    average_service_time = total_service_time / len(customer_finished)

    # Customer Satisfaction Rate
    satisfied_customers = len(customer_finished)
    customer_satisfaction_rate = satisfied_customers / len(system.customers)

    # Total Time in System
    total_time_in_system = average_waiting_time + average_service_time

    return {
        "Server Utilization Rate": server_utilization_rate,
        "Average Waiting Time": average_waiting_time,
        "Average Service Time": average_service_time,
        "Customer Satisfaction Rate": customer_satisfaction_rate,
        "Total Time in System": total_time_in_system,
    }


def main():
    env = simpy.Environment()
    total_time = 100
    num_customers = 30
    arrival_rate = 0.4
    service_times = [
        1,
        3,
        4,
        3,
        5,
        4,
        3,
        4,
        4,
        3,
        5,
        1,
    ]  # 1 Waiting, 4 Order, 6 Stall, 1 Payment
    queue_capacities = [
        5,
        3,
        4,
        3,
        4,
        5,
    ]  # 1 Waiting, 2 Order, 3 Stall, 1 Payment

    system = System(
        env, num_customers, arrival_rate, service_times, queue_capacities, total_time
    )
    system.run()
    metrics = calculate_system_metrics(system)

    print("\nSystem Metrics:")
    for metric, value in metrics.items():
        print(f"{metric}: {value}")


if __name__ == "__main__":
    main()
