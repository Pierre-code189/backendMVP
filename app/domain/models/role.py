from enum import Enum


class Roles(str, Enum):
    USER = "user"
    MOD = "moderator"
    ADMIN = "administrator"
