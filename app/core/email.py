import smtplib
from email.message import EmailMessage
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, content: str):
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(f"Simulando envío de correo a {to_email} porque no hay SMTP configurado. Asunto: {subject}")
        print(f"\n--- SIMULACIÓN DE CORREO ---\nPara: {to_email}\nAsunto: {subject}\n\n{content}\n----------------------------\n")
        return
        
    try:
        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = subject
        msg['From'] = settings.SMTP_USER
        msg['To'] = to_email

        # Usar Gmail SMTP por defecto, pero se podría configurar por variables
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Correo enviado exitosamente a {to_email}")
    except Exception as e:
        logger.error(f"Error al enviar correo a {to_email}: {e}")

def send_pin_email(to_email: str, locker_number: str, pin_close: str, pin_open: str):
    subject = f"✅ Tu casillero {locker_number} ha sido aprobado"
    content = f"""¡Hola!

Tu pago para el casillero {locker_number} ha sido verificado y aprobado.

Aquí tienes tus PINs de acceso para el teclado físico del casillero:
🔒 PIN para CERRAR: {pin_close}
🔓 PIN para ABRIR: {pin_open}

Por favor, guarda estos PINs. Recuerda que si cierras el casillero y tu tiempo expira, no podrás volver a cerrarlo.
"""
    send_email(to_email, subject, content)

def send_warning_email(to_email: str, locker_number: str):
    subject = f"⚠️ Atención: A tu casillero {locker_number} le quedan 5 minutos"
    content = f"""¡Hola!

Te informamos que al alquiler de tu casillero {locker_number} le quedan solo 5 minutos para expirar.
Por favor, asegúrate de retirar tus pertenencias antes de que el tiempo se acabe. Si necesitas más tiempo, puedes extender tu alquiler desde la plataforma.

Si tu tiempo expira mientras el casillero está abierto, no podrás volver a cerrarlo con tu PIN.
"""
    send_email(to_email, subject, content)

def send_alert_email(to_email: str, locker_number: str):
    subject = f"🚨 ALERTA DE SEGURIDAD - Casillero {locker_number}"
    content = f"""¡ALERTA!

Nuestro sensor de seguridad ha detectado un movimiento o apertura forzada inusual en tu casillero {locker_number} mientras se encontraba cerrado.
Por favor, revisa tu casillero lo antes posible o contacta a la administración.
"""
    send_email(to_email, subject, content)
