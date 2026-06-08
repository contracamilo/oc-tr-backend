"""
JWT auth utilities — iter 2.

TODO iter 2:
- hash_password(plain: str) -> str
- verify_password(plain: str, hashed: str) -> bool
- create_access_token(data: dict) -> str
- create_refresh_token(data: dict) -> str
- decode_token(token: str) -> dict
- get_current_user(token: str, db: AsyncSession) -> User
- require_admin(current_user: User) -> User
"""
