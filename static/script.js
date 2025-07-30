document.addEventListener('DOMContentLoaded', () => {
    const BACKEND_URL = "https://alarma-production.up.railway.app";
    console.log("✅ Script cargado. Backend URL:", BACKEND_URL);

    const urlParams = new URLSearchParams(window.location.search);
    const comunidadSeleccionada = urlParams.get('comunidad');

    if (!comunidadSeleccionada) {
        alert("❌ No se especificó la comunidad en la URL.");
        return;
    }
    console.log("✅ Comunidad seleccionada:", comunidadSeleccionada);

    let ubicacionesPredeterminadas = []; // Puntos de interés fijos de la comunidad (ej. parque, entrada)
    let ubicacionReferenciaComunidad = null; // Primer punto de interés como fallback
    let userData = null; // Datos del usuario que activó la alarma
    let comunidadMiembros = []; // Lista de todos los miembros de la comunidad con sus datos
    let currentUserMemberData = null; // ⭐ DATOS REGISTRADOS DEL USUARIO ACTUAL ⭐

    const textarea = document.getElementById('descripcion');
    const boton = document.getElementById('btnEmergencia');
    const statusMsg = document.getElementById('statusMsg');
    const toggleRealTime = document.getElementById('toggleRealTime');

    // Paso 1: Obtener datos del usuario desde la URL
    const userIdFromUrl = urlParams.get('id');
    const userFirstNameFromUrl = urlParams.get('first_name');

    if (userIdFromUrl) {
        userData = {
            id: userIdFromUrl,
            first_name: userFirstNameFromUrl,
            last_name: urlParams.get('last_name') || '',
            username: urlParams.get('username') || ''
        };
        console.log("✅ Datos del usuario obtenidos de la URL:", userData);
        statusMsg.textContent = `👋 Hola ${userData.first_name} en ${comunidadSeleccionada.toUpperCase()}`;
    } else if (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe) {
        // Fallback (menos probable en grupos, pero por si acaso)
        userData = window.Telegram.WebApp.initDataUnsafe.user;
        console.log("✅ Datos del usuario de Telegram cargados:", userData);
        if (userData && userData.first_name) {
            statusMsg.textContent = `👋 Hola ${userData.first_name} en ${comunidadSeleccionada.toUpperCase()}`;
        } else {
            statusMsg.textContent = `👥 Comunidad detectada: ${comunidadSeleccionada.toUpperCase()}`;
        }
    } else {
        console.warn("⚠️ No se pudieron obtener los datos del usuario.");
        statusMsg.textContent = `👥 Comunidad detectada: ${comunidadSeleccionada.toUpperCase()}`;
    }

    // Paso 2: Cargar datos iniciales (miembros y ubicaciones fijas)
    cargarDatosIniciales(comunidadSeleccionada);

    async function cargarDatosIniciales(comunidad) {
        // Cargar ubicaciones predeterminadas de la comunidad (puntos de interés)
        try {
            const resUbicaciones = await fetch(`${BACKEND_URL}/api/ubicaciones/${comunidad}`);
            if (!resUbicaciones.ok) throw new Error(`Error al cargar ubicaciones fijas: ${resUbicaciones.status}`);
            ubicacionesPredeterminadas = await resUbicaciones.json();
            if (ubicacionesPredeterminadas.length > 0) {
                ubicacionReferenciaComunidad = ubicacionesPredeterminadas[0]; 
                console.log("✅ Ubicaciones fijas (puntos de interés) cargadas.");
            } else {
                console.warn("⚠️ No hay ubicaciones de referencia para esta comunidad.");
            }
        } catch (error) {
            console.error("❌ Error en cargarUbicacionesFijas:", error.message);
        }

        // Cargar miembros de la comunidad para encontrar los datos del usuario actual
        try {
            const resMiembros = await fetch(`${BACKEND_URL}/api/miembros/${comunidad}`);
            if (!resMiembros.ok) throw new Error(`Error al cargar miembros: ${resMiembros.status}`);
            comunidadMiembros = await resMiembros.json();
            console.log("✅ Miembros de la comunidad cargados:", comunidadMiembros);

            // ⭐ IMPORTANTE: Encontrar los datos registrados del usuario actual ⭐
            if (userData && userData.id) {
                currentUserMemberData = comunidadMiembros.find(m => String(m.telegram_id) === String(userData.id));
                if (currentUserMemberData) {
                    console.log("✅ Datos registrados del usuario actual encontrados:", currentUserMemberData);
                    // Actualizar el statusMsg con la dirección registrada del usuario
                    if (!toggleRealTime.checked && currentUserMemberData.direccion) {
                         statusMsg.textContent = `📍 Tu dirección registrada: ${currentUserMemberData.direccion}`;
                    }
                } else {
                    console.warn("⚠️ Usuario actual no encontrado en la lista de miembros de la comunidad.");
                }
            }
        } catch (error) {
            console.error("❌ Error en cargarMiembrosComunidad:", error.message);
        }
        // Actualizar el mensaje de estado inicial si es necesario
        updateStatusMessageBasedOnToggle();
    }

    // Función para actualizar el mensaje de estado en la UI
    function updateStatusMessageBasedOnToggle() {
        if (toggleRealTime.checked) {
            statusMsg.textContent = "📍 Usando ubicación en tiempo real";
        } else if (currentUserMemberData && currentUserMemberData.direccion) {
            statusMsg.textContent = `📍 Tu dirección registrada: ${currentUserMemberData.direccion}`;
        } else if (ubicacionReferenciaComunidad) {
            statusMsg.textContent = `📍 Usando ubicación de referencia: ${ubicacionReferenciaComunidad.nombre}`;
        } else {
            statusMsg.textContent = "⏳ Esperando acción del usuario...";
        }
    }


    textarea.addEventListener('input', () => {
        const texto = textarea.value.trim();
        if (texto.length >= 4 && texto.length <= 300) {
            boton.disabled = false;
            boton.classList.add('enabled');
            statusMsg.textContent = "✅ Listo para enviar"; // Mensaje más genérico
            updateStatusMessageBasedOnToggle(); // Asegurarse de que el mensaje de ubicación se mantenga
        } else {
            boton.disabled = true;
            boton.classList.remove('enabled');
            statusMsg.textContent = "⏳ Esperando acción del usuario...";
            updateStatusMessageBasedOnToggle(); // Asegurarse de que el mensaje de ubicación se mantenga
        }
    });

    toggleRealTime.addEventListener('change', () => {
        updateStatusMessageBasedOnToggle();
    });

    boton.addEventListener('click', () => {
        console.log("➡️ Evento 'click' en el botón detectado.");
        const descripcion = textarea.value.trim();

        if (!descripcion || !comunidadSeleccionada) {
            console.error("❌ Validación fallida: faltan datos necesarios (descripción o comunidad).");
            alert("❌ Faltan datos necesarios");
            return;
        }

        boton.disabled = true;
        boton.textContent = "Enviando...";
        statusMsg.textContent = "🔄 Enviando alerta...";

        let latEnvio = null;
        let lonEnvio = null;
        let direccionEnvio = "Dirección no disponible";

        // Determinar la dirección REGISTRADA del usuario, SIEMPRE que sea posible
        if (currentUserMemberData && currentUserMemberData.direccion) {
            direccionEnvio = currentUserMemberData.direccion;
        } else if (ubicacionReferenciaComunidad && ubicacionReferenciaComunidad.direccion) {
            direccionEnvio = ubicacionReferenciaComunidad.direccion;
        }


        if (toggleRealTime.checked && navigator.geolocation) {
            console.log("➡️ Solicitando ubicación en tiempo real...");
            navigator.geolocation.getCurrentPosition(pos => {
                latEnvio = pos.coords.latitude;
                lonEnvio = pos.coords.longitude;
                // La direcciónEnvio ya fue establecida con la dirección registrada del usuario o de referencia
                console.log("✅ Ubicación obtenida (tiempo real). Llamando a enviarAlerta.");
                enviarAlerta(descripcion, latEnvio, lonEnvio, direccionEnvio, userData);
            }, () => {
                console.error("❌ Error al obtener ubicación en tiempo real. Cayendo a ubicación registrada/referencia.");
                alert("❌ No se pudo obtener ubicación en tiempo real. Usando tu ubicación registrada o de referencia.");
                // Fallback a la ubicación registrada del miembro o de referencia
                handleFallbackLocation(descripcion, userData, direccionEnvio);
            });
        } else {
            // ⭐ Lógica para cuando el toggle NO está activado (o no hay GPS) ⭐
            if (currentUserMemberData && currentUserMemberData.geolocalizacion) {
                latEnvio = currentUserMemberData.geolocalizacion.lat;
                lonEnvio = currentUserMemberData.geolocalizacion.lon;
                // La direcciónEnvio ya fue establecida con la dirección registrada del usuario
                console.log("➡️ Usando ubicación registrada del miembro. Llamando a enviarAlerta.");
                enviarAlerta(descripcion, latEnvio, lonEnvio, direccionEnvio, userData);
            } else if (ubicacionReferenciaComunidad && ubicacionReferenciaComunidad.geolocalizacion) {
                // Fallback a la ubicación de referencia de la comunidad
                latEnvio = ubicacionReferenciaComunidad.geolocalizacion.lat;
                lonEnvio = ubicacionReferenciaComunidad.geolocalizacion.lon;
                direccionEnvio = ubicacionReferenciaComunidad.direccion || "Ubicación de referencia";
                console.log("➡️ Usando ubicación de referencia de la comunidad. Llamando a enviarAlerta.");
                enviarAlerta(descripcion, latEnvio, lonEnvio, direccionEnvio, userData);
            } else {
                console.error("❌ No se encontró ubicación válida (ni registrada ni de referencia).");
                alert("❌ No se encontró una ubicación válida para enviar la alarma.");
                resetFormulario();
            }
        }
    });

    // Función de fallback para geolocalización o si el usuario no tiene datos registrados
    function handleFallbackLocation(descripcion, userData, direccionFija) {
        let latEnvio = null;
        let lonEnvio = null;
        let direccionEnvio = direccionFija; // Ya debería traer la dirección registrada/referencia

        if (currentUserMemberData && currentUserMemberData.geolocalizacion) {
            latEnvio = currentUserMemberData.geolocalizacion.lat;
            lonEnvio = currentUserMemberData.geolocalizacion.lon;
            direccionEnvio = currentUserMemberData.direccion || direccionFija;
            console.log("➡️ Fallback: Usando ubicación registrada del miembro.");
        } else if (ubicacionReferenciaComunidad && ubicacionReferenciaComunidad.geolocalizacion) {
            latEnvio = ubicacionReferenciaComunidad.geolocalizacion.lat;
            lonEnvio = ubicacionReferenciaComunidad.geolocalizacion.lon;
            direccionEnvio = ubicacionReferenciaComunidad.direccion || direccionFija;
            console.log("➡️ Fallback: Usando ubicación de referencia de la comunidad.");
        } else {
            console.error("❌ Fallback: No se encontró ubicación válida.");
            alert("❌ No se encontró una ubicación válida para enviar la alarma.");
            resetFormulario();
            return;
        }
        enviarAlerta(descripcion, latEnvio, lonEnvio, direccionEnvio, userData);
    }


    function enviarAlerta(descripcion, lat, lon, direccion, userData) {
        console.log("➡️ ENVIAR ALERTA: La función ha sido llamada.");
        
        const userTelegramData = userData ? {
            id: userData.id,
            first_name: userData.first_name,
            last_name: userData.last_name || '',
            username: userData.username || ''
        } : {
            id: 'Desconocido',
            first_name: 'Anónimo',
            last_name: '',
            username: ''
        };

        console.log("📤 Datos de usuario a enviar:", userTelegramData);
        console.log("📤 Datos de ubicación a enviar:", { lat, lon, direccion });

        fetch(`${BACKEND_URL}/api/alert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tipo: "Alerta Roja Activada",
                descripcion,
                ubicacion: { lat, lon },
                direccion: direccion, // ⭐ Esta 'direccion' ya está correctamente determinada ⭐
                comunidad: comunidadSeleccionada,
                user_telegram: userTelegramData
            })
        })
            .then(res => {
                console.log("✅ Respuesta del servidor recibida (Headers):", res.status);
                if (!res.ok) {
                    throw new Error(`Error del servidor: ${res.status} ${res.statusText}`);
                }
                return res.json();
            })
            .then(data => {
                console.log("✅ Respuesta del servidor (JSON):", data);
                alert(data.status || "✅ Alerta enviada correctamente.");
                resetFormulario();
            })
            .catch(err => {
                console.error("❌ Error en la llamada fetch:", err);
                alert("❌ Error al enviar alerta. Consulta la consola para más detalles.");
                resetFormulario();
            });
    }

    function resetFormulario() {
        boton.disabled = true;
        boton.textContent = "🚨 Enviar Alerta Roja";
        textarea.value = "";
        boton.classList.remove('enabled');
        updateStatusMessageBasedOnToggle(); // Restablecer el mensaje de estado
    }
});
