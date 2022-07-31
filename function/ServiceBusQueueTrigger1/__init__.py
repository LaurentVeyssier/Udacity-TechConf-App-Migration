import logging
import azure.functions as func
import psycopg2
import os, pytz
from datetime import datetime
from sendgrid import SendGridAPIClient, Email, To, Content
from sendgrid.helpers.mail import Mail, HtmlContent


def main(msg: func.ServiceBusMessage):

    notification_id = int(msg.get_body().decode('utf-8'))
    logging.info('Python ServiceBus queue trigger processed message: %s',notification_id)
    print(notification_id)

    # TODO: Get connection to database
    database = os.environ.get('POSTGRES_DB')
    user = os.environ.get('POSTGRES_USER')
    pwd = os.environ.get('POSTGRES_PW')
    host = os.environ.get('POSTGRES_URL')


    conn = psycopg2.connect(database = database, user = user, password = pwd, 
                            host = host, port = "5432")  # port adjusted to v11
    print("Connection Successful to PostgreSQL")

    try:
        # TODO: Get notification message and subject from database using the notification_id
        cur = conn.cursor()
        cur.execute("SELECT message, subject FROM notification WHERE id={};".format(notification_id))
        notification = cur.fetchone()
        update, topic = notification

        # TODO: Get attendees email and name
        cur.execute("SELECT last_name, email, conference_id FROM attendee")
        attendees = cur.fetchall()

        cur.execute("SELECT name, date FROM conference")
        conference_list = cur.fetchall()
        conf_dict = {}
        i=1
        for (conf_name, conf_date) in conference_list:
            conf_dict[i] = (conf_name, conf_date)
            i+=1

        # TODO: Loop through each attendee and send an email with a personalized subject
        sg = SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))
        sender = os.environ.get('ADMIN_EMAIL_ADDRESS')
        for attendee in attendees:
            name, email, conf_id = attendee
            from_email = Email(sender)
            to_emails = To(sender)  # I replaced the attendee dummy email here to test
            subject = f"Your participation to {conf_dict[conf_id][0]} - {conf_dict[conf_id][1]} - {topic}"
            #html_content = Content("text/plain", f"To: {email}<br>Dear participant <strong>{name}</strong>,<br>we are delighted to have you onboard.<br>Latest conference info:{subject}<br>Attached is your personal copy of the conference agenda.")
            html_content = HtmlContent(f"To: {email}<br>Dear participant <strong>{name}</strong><br>{update}<br>we are delighted to have you onboard.<br>Attached is your personal copy of the conference agenda.")
            message = Mail(from_email, to_emails, subject, html_content)
            sg.send(message)

        # TODO: Update the notification table by setting the completed date and updating the status with the total number of attendees notified
        cur.execute("UPDATE notification SET completed_date = '{}', status = 'Notified {} attendees' WHERE id = {};".format(pytz.utc.localize(datetime.utcnow()),len(attendees),notification_id))
        conn.commit()
        

    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(error)
    finally:
        # TODO: Close connection
        # Close communication with the database
        cur.close()
        conn.close()