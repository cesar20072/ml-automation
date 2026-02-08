import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import get_settings
from utils.logger import logger

settings = get_settings()

def send_email(subject: str, body: str, to_email: str = None):
    """Send email notification"""
    
    if not to_email:
        to_email = settings.NOTIFICATION_EMAIL
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

def notify_product_published(product_name: str, ml_item_id: str, score: int):
    """Notify when product is auto-published"""
    subject = f"✅ Producto Publicado: {product_name}"
    body = f"""
Producto publicado automáticamente en Mercado Libre

Producto: {product_name}
ML Item ID: {ml_item_id}
Score: {score}/100

El producto fue publicado automáticamente por tener un score alto.
    """
    send_email(subject, body)

def notify_optimization(action: str, product_name: str, details: str):
    """Notify optimization actions"""
    subject = f"⚙️ Optimización: {action}"
    body = f"""
Acción de optimización ejecutada

Acción: {action}
Producto: {product_name}
Detalles: {details}

Esta acción fue ejecutada automáticamente por el sistema.
    """
    send_email(subject, body)

def notify_ab_test_completed(product_name: str, winner: str, results: dict):
    """Notify when A/B test completes"""
    subject = f"🏆 Test A/B Completado: {product_name}"
    body = f"""
Test A/B completado

Producto: {product_name}
Ganador: Variante {winner}

Resultados:
{results}

El sistema pausará automáticamente la variante perdedora.
    """
    send_email(subject, body)

def notify_error(error_type: str, error_message: str):
    """Notify critical errors"""
    subject = f"❌ Error Crítico: {error_type}"
    body = f"""
Error crítico en el sistema

Tipo: {error_type}
Mensaje: {error_message}

Revisa los logs para más detalles.
    """
    send_email(subject, body)
