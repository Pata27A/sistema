document.addEventListener('DOMContentLoaded', function () {
    const btnVentas = document.getElementById('btnExportarVentasRG90');
    const inputVentas = document.getElementById('inputPeriodoVentas');

    const btnCompras = document.getElementById('btnExportarComprasRG90');
    const inputCompras = document.getElementById('inputPeriodoCompras');

    function exportarRG90(url, input, tipo) {
        const periodo = input.value.trim();

        if (!/^\d{6}$/.test(periodo)) {
            alert('⚠️ Ingrese un período válido en formato MMYYYY');
            return;
        }

        const formData = new FormData();
        formData.append('periodo', periodo);

        // Mostrar estado de carga
        const botonOriginal = tipo === 'ventas' ? btnVentas : btnCompras;
        const textoOriginal = botonOriginal.textContent;
        botonOriginal.disabled = true;
        botonOriginal.textContent = 'Generando...';

        fetch(url, {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.ok) {
                const archivo = data.archivo;
                const enlace = document.createElement('a');
                enlace.href = `/rg90/download/${archivo}`;
                enlace.download = archivo;
                document.body.appendChild(enlace);
                enlace.click();
                document.body.removeChild(enlace);
            } else {
                alert('❌ Errores encontrados:\n' + data.errores.join('\n'));
            }
        })
        .catch(err => {
            console.error(err);
            alert(`❌ No se pudo generar el archivo de ${tipo}: ` + err.message);
        })
        .finally(() => {
            botonOriginal.disabled = false;
            botonOriginal.textContent = textoOriginal;
        });
    }

    btnVentas.addEventListener('click', () => {
        exportarRG90('/rg90/ventas', inputVentas, 'ventas');
    });

    btnCompras.addEventListener('click', () => {
        exportarRG90('/rg90/compras', inputCompras, 'compras');
    });
});
