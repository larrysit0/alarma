const SERVER_URL = "https://1234abcd.ngrok.io/alerta";

document.getElementById("btnEmergencia").addEventListener("click", () => {
  const descripcion = document.getElementById("descripcion").value.trim();

  if (!navigator.geolocation) {
    alert("Geolocalización no soportada");
    return;
  }

  navigator.geolocation.getCurrentPosition(pos => {
    const payload = {
      mensaje: descripcion || "Alerta Roja Activada",
      lat: pos.coords.latitude,
      lon: pos.coords.longitude
    };

    fetch(SERVER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
      document.getElementById("statusMsg").textContent = data.status;
    })
    .catch(err => {
      document.getElementById("statusMsg").textContent = "❌ Error al enviar alerta";
    });
  }, () => {
    alert("No se pudo obtener la ubicación.");
  });
});
