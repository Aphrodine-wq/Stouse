from vibehouse.common.logging import get_logger
from vibehouse.core.orchestration.schemas import RFQPackage
from vibehouse.integrations.sendgrid import EmailClient
from vibehouse.integrations.twilio_client import SMSClient

logger = get_logger("orchestration.outreach")


class OutreachManager:
    def __init__(self):
        self.email_client = EmailClient()
        self.sms_client = SMSClient()

    async def send_rfq_email(self, vendor_email: str, vendor_name: str, rfq: RFQPackage) -> dict:
        subject = f"Request for Quote: {rfq.project_title} - {rfq.required_trade}"

        html_body = f"""
        <h2>Request for Quotation</h2>
        <p>Dear {vendor_name},</p>
        <p>You have been selected as a potential contractor for the following project:</p>
        <table>
            <tr><td><strong>Project:</strong></td><td>{rfq.project_title}</td></tr>
            <tr><td><strong>Location:</strong></td><td>{rfq.project_address or 'TBD'}</td></tr>
            <tr><td><strong>Trade Required:</strong></td><td>{rfq.required_trade}</td></tr>
            <tr><td><strong>Scope:</strong></td><td>{rfq.scope_description}</td></tr>
            <tr><td><strong>Est. Start:</strong></td><td>{rfq.estimated_start_date or 'TBD'}</td></tr>
            <tr><td><strong>Budget Range:</strong></td><td>{rfq.budget_range or 'Open'}</td></tr>
        </table>
        <p>Please submit your bid within {rfq.response_deadline_days} days.</p>
        <p>Best regards,<br>VibeHouse Construction Platform</p>
        """

        result = await self.email_client.send_email(
            to=vendor_email,
            subject=subject,
            html_body=html_body,
        )

        logger.info("Sent RFQ email to %s for project %s", vendor_email, rfq.project_title)
        return result

    async def send_rfq_sms(self, vendor_phone: str, rfq: RFQPackage) -> dict:
        body = (
            f"VibeHouse: New RFQ for {rfq.required_trade} on '{rfq.project_title}'. "
            f"Check your email for details. Reply STOP to opt out."
        )

        result = await self.sms_client.send_sms(to=vendor_phone, body=body)

        logger.info("Sent RFQ SMS to %s for project %s", vendor_phone, rfq.project_title)
        return result

    async def send_followup(self, vendor_email: str, vendor_name: str, project_title: str) -> dict:
        subject = f"Reminder: Bid requested for {project_title}"

        html_body = f"""
        <p>Dear {vendor_name},</p>
        <p>This is a friendly reminder that we sent you a Request for Quotation
        for <strong>{project_title}</strong>.</p>
        <p>If you're interested, please submit your bid at your earliest convenience.</p>
        <p>Best regards,<br>VibeHouse Construction Platform</p>
        """

        result = await self.email_client.send_email(
            to=vendor_email,
            subject=subject,
            html_body=html_body,
        )

        logger.info("Sent followup email to %s for project %s", vendor_email, project_title)
        return result
