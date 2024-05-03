import "bootstrap/dist/css/bootstrap.min.css";
import QRScanner from "./components/QRScanner";

function App() {
  return (
    <div className="w-100 h-100 d-flex align-items-center justify-content-center ">
      <QRScanner />
    </div>
  );
}

export default App;
