import { Scanner } from "@yudiel/react-qr-scanner";
import { useState } from "react";
import { Breadcrumb, Button, Card } from "react-bootstrap";
import { BASE_URL } from "../config";

function QRScanner() {
  const [enabled, setEnabled] = useState<boolean>(true);
  const handleSuccess = (text: string) => {
    if (enabled && text) {
      window.open(
        BASE_URL + "/bookings/booking/" + text + "/summary",
        "_blank",
        "width=1000,height=600"
      );
      setEnabled(false);
    }
  };

  return (
    <div className="w-100 d-flex flex-column align-items-center justify-content-center">
      <div className="w-100 px-5">
        <Card className="w-100">
          <Card.Header>
            <Breadcrumb>
              <Breadcrumb.Item href="#">Home</Breadcrumb.Item>
              <Breadcrumb.Item active>QR Code Scanner</Breadcrumb.Item>
            </Breadcrumb>
          </Card.Header>
        </Card>
      </div>
      <div className="p-3 h-75 d-flex flex-column align-items-center justify-content-center text-center gap-4">
        <Card>
          <Card.Header>
            <h2>Scan QR Code to get booking details</h2>
          </Card.Header>
          <Card.Body className="position-relative">
            <Scanner
              onResult={handleSuccess}
              onError={(error) => {
                alert(error);
              }}
              options={{
                delayBetweenScanSuccess: 1000,
                delayBetweenScanAttempts: 1000,
              }}
              styles={{
                container: {
                  width: "100%",
                  height: "100%",
                  borderRadius: "0 0 5px 5px",
                },
              }}
              components={{
                audio: false,
              }}
            />
            {!enabled && (
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  zIndex: 50,
                  backgroundColor: "rgba(0, 0, 0, 0.5)",
                }}
                className="w-100 h-100 d-flex align-items-center justify-content-center"
              >
                <Button onClick={() => setEnabled(true)}>Scan Another</Button>
              </div>
            )}
          </Card.Body>
        </Card>
      </div>
    </div>
  );
}

export default QRScanner;
