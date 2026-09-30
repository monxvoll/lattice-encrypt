"""Ejecucion del interprete en un proceso aparte, para poder cortarla.

Vive en su propio modulo, y no dentro de `servidor.py`, por una razon concreta:
el proceso hijo se crea con 'spawn', asi que reimporta el modulo donde esta la
funcion que se le pasa. Si esa funcion viviera junto a FastAPI, cada ejecucion
pagaria el import de FastAPI y starlette (alrededor de un segundo) para
devolver un informe que no los necesita. Ahi solo se importa el interprete.

El resultado se devuelve por una `Queue` y no por el valor de retorno del
proceso, que se pierde: lo que le importa al padre es poder distinguir "todavia
no ha terminado" de "ha terminado con estos datos".
"""
from core.interpreteArchivo import ejecutar_programa


def ejecutar(texto, mostrar_tokens, cola):
    """Cuerpo del proceso hijo: ejecuta el programa y encola el informe."""
    try:
        cola.put(ejecutar_programa(texto, mostrar_tokens=mostrar_tokens))
    except BaseException as error:  # noqa: BLE001 - la excepcion viaja como dato
        # Una excepcion no cruza la frontera del proceso, se convierte en texto.
        cola.put({"_error": f"{type(error).__name__}: {error}"})
    finally:
        # Sin esto el proceso puede morir antes de que el hilo alimentador de la
        # cola haya entregado el informe, y el padre se quedaria esperando a un
        # resultado que ya no va a llegar.
        cola.close()
        cola.join_thread()
