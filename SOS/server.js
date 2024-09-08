const express = require('express');
const nodemailer = require('nodemailer');
const bodyParser = require('body-parser');
const path = require('path');

const app = express();
const port = 5500;

app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'SOS.html'));
});

const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
        user: 'radhikaworkspace07@gmail.com',
        pass: 'wpuk yfxa etee pyor'  // Use an app-specific password
    }
});

app.post('/send-sos', (req, res) => {
    const { location } = req.body;
    const [lat, lng] = location.split(',');
    // Create a Google Maps link that prompts for origin
    const googleMapsLink = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}&travelmode=driving`; 
    const recipients = [
       'vatsaboii36@gmail.com',
       'radhika.singhal0712@gmail.com',
       'srikruthineriyanmuri@gmail.com'
    ];

    const mailOptions = {
        from: 'radhikaworkspace07@gmail.com',
        to: recipients.join(', '),
        subject: 'SOS - Emergency Location',
        text: `Emergency! A person needs help at this location: ${location}\n\nGet directions: ${googleMapsLink}\n\n`,
        html: `
            <h1>Emergency SOS!</h1>
            <p>A person needs help at this location: ${location}</p>
            <p><a href="${googleMapsLink}" target="_blank">Get directions to this location</a></p>
            <p>This link will show directions from your current location to the emergency location.</p>
        `
    };

    transporter.sendMail(mailOptions, (error, info) => {
        if (error) {
            console.error('Error sending email:', error);
            res.status(500).json({ success: false, message: 'Failed to send SOS email' });
        } else {
            console.log('Email sent:', info.response);
            res.json({ success: true, message: 'SOS email sent successfully to all recipients' });
        }
    });
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});