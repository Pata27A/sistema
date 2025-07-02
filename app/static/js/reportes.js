document.addEventListener('DOMContentLoaded', function () {

    // Abrir modal Ventas por Período
    const btnVentasPorPeriodo = document.getElementById('btnVentasPorPeriodo');
    if (btnVentasPorPeriodo) {
        btnVentasPorPeriodo.addEventListener('click', function (e) {
            e.preventDefault();
            const modal = new bootstrap.Modal(document.getElementById('modalVentasPeriodo'));
            modal.show();
        });
    }

    // Abrir modal Ventas por Cliente
    const btnVentasPorCliente = document.getElementById('btnVentasPorCliente');
    if (btnVentasPorCliente) {
        btnVentasPorCliente.addEventListener('click', function (e) {
            e.preventDefault();
            const modal = new bootstrap.Modal(document.getElementById('modalVentasCliente'));
            modal.show();
        });
    }

    // Descargar PDF Productos Más Vendidos directo
    const btnProductosMasVendidos = document.getElementById('btnProductosMasVendidos');
    if (btnProductosMasVendidos) {
        btnProductosMasVendidos.addEventListener('click', function (e) {
            e.preventDefault();
            window.open('/reports/sales/top-products', '_blank');
        });
    }

    // Formulario: Ventas por Período (exportar PDF)
    const formPeriodo = document.getElementById('formVentasPeriodo');
    if (formPeriodo) {
        formPeriodo.addEventListener('submit', function (e) {
            e.preventDefault();

            const start_date = formPeriodo.querySelector('input[name="start_date"]').value;
            const end_date = formPeriodo.querySelector('input[name="end_date"]').value;
            const cliente = formPeriodo.querySelector('input[name="cliente"]')?.value.trim() || '';
            const vendedor = formPeriodo.querySelector('input[name="vendedor"]')?.value.trim() || '';

            if (!start_date || !end_date) {
                alert("Debe completar las fechas Desde y Hasta");
                return;
            }

            let url = `/reports/sales/periodo?start_date=${encodeURIComponent(start_date)}&end_date=${encodeURIComponent(end_date)}`;
            if (cliente) url += `&cliente=${encodeURIComponent(cliente)}`;
            if (vendedor) url += `&vendedor=${encodeURIComponent(vendedor)}`;

            window.open(url, '_blank');

            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalVentasPeriodo'));
            if (modal) modal.hide();
        });
    }

    // Formulario: Ventas por Cliente (exportar PDF)
    const formCliente = document.getElementById('formVentasCliente');
    if (formCliente) {
        formCliente.addEventListener('submit', function (e) {
            e.preventDefault();

            const start_date = formCliente.querySelector('input[name="start_date"]').value;
            const end_date = formCliente.querySelector('input[name="end_date"]').value;
            const cliente = formCliente.querySelector('input[name="cliente"]')?.value.trim() || '';
            const detalle = formCliente.querySelector('select[name="detalle"]')?.value || 'no';

            if (!start_date || !end_date) {
                alert("Debe completar las fechas Desde y Hasta");
                return;
            }

            let url = `/reports/sales/by-client?start_date=${encodeURIComponent(start_date)}&end_date=${encodeURIComponent(end_date)}&detalle=${encodeURIComponent(detalle)}`;
            if (cliente) url += `&cliente=${encodeURIComponent(cliente)}`;

            window.open(url, '_blank');

            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalVentasCliente'));
            if (modal) modal.hide();
        });
    }

});
