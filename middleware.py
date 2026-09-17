import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm.exc import StaleDataError

class RequestLifecycleMiddleware(BaseHTTPMiddleware):
    """
    Middleware para el ciclo de vida de peticiones HTTP:
    - Mide y expone tiempos de ejecución en la cabecera X-Process-Time.
    - Asegura la captura y manejo uniforme de excepciones de concurrencia (StaleDataError -> 409 Conflict).
    - Agrega cabeceras de seguridad a todas las respuestas.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response: Response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = f"{process_time:.4f}s"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            return response
        except StaleDataError:
            # Captura de conflicto de concurrencia optimista
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "Conflicto de concurrencia: el registro fue modificado simultáneamente por otra transacción. Actualice la vista e intente nuevamente."
                },
                headers={
                    "X-Process-Time": f"{time.time() - start_time:.4f}s",
                    "X-Content-Type-Options": "nosniff"
                }
            )
        except Exception as exc:
            # Propagar o manejar excepciones no controladas
            raise exc
