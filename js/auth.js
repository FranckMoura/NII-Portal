// js/auth.js

// Verifica se existe a chave de autenticação na sessão
if (sessionStorage.getItem("nii_autenticado") !== "true") {
    // Se não estiver logado, manda para o login
    window.location.href = "login.html";
}

// Função para Sair (Logout)
function fazerLogout() {
    sessionStorage.removeItem("nii_autenticado");
    window.location.href = "login.html";
}