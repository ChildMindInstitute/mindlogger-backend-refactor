class RabbitMQSettings:
    host: str = "localhost"
    user: str = "guest"
    password: str = "guest"
    default_routing_key: str = "mindlogger"
    port: int = 5672

    @property
    def url(self):
        return f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"
