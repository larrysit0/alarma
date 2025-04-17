function enviarAlarma(conGeolocalizacion) {
    let mensaje = conGeolocalizacion 
        ? document.getElementById("mensajeRojo").value 
        : document.getElementById("mensajeAzul").value;

    if (mensaje.trim() === "") {
        alert("Por favor, escribe un mensaje.");
        return;
    }

    // Si incluye geolocalización, obtenerla
    if (conGeolocalizacion && navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            mensaje += `\n📍 Ubicación: https://www.google.com/maps?q=${position.coords.latitude},${position.coords.longitude}`;
            enviarMensajeAlServidor(mensaje, conGeolocalizacion);
        }, function(error) {
            alert("No se pudo obtener la ubicación.");
            enviarMensajeAlServidor(mensaje, conGeolocalizacion);
        });
    } else {
        enviarMensajeAlServidor(mensaje, conGeolocalizacion);
    }
}

function enviarMensajeAlServidor(mensaje, geolocalizacion) {
    let data = { mensaje, geolocalizacion };

    fetch("http://localhost:5000/enviarAlarma", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        alert("Alarma enviada correctamente.");
    })
    .catch(error => {
        alert("Error al enviar la alarma.");
        console.error("Error:", error);
    });
}
