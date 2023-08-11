from pydantic import BaseModel


class RabbitMQSettings(BaseModel):
    host: str = "rabbitmq"
    user: str = "guest"
    password: str = "guest"
    default_routing_key: str = "mindlogger"
    port: int = 5672
    use_ssl: bool = True

    @property
    def url(self):
        protocol = "amqps" if self.use_ssl else "amqp"
        return f"{protocol}://{self.user}:{self.password}@{self.host}:{self.port}/"  # noqa: E501
