"""
Paginación genérica — iter A (issue #12).

TODO iter A:
- paginate(query, limit, offset, db) -> tuple[list, int]
  Ejecuta SELECT + COUNT en una sola pasada y devuelve (items, total).
  Usar en todos los repositorios list(); nunca usar .all() directo.
"""
