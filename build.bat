@echo off
echo ============================================
echo    BigBackups - Script de Construccion
echo ============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH
    pause
    exit /b 1
)

echo [1/4] Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Fallo la instalacion de dependencias
    pause
    exit /b 1
)

echo.
echo [2/4] Limpiando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [3/4] Generando ejecutable...
pyinstaller bigbackups.spec --noconfirm
if errorlevel 1 (
    echo ERROR: Fallo la generacion del ejecutable
    pause
    exit /b 1
)

echo.
echo [4/4] Verificando resultado...
if exist "dist\BigBackups.exe" (
    echo.
    echo ============================================
    echo    EXITO! Ejecutable generado:
    echo    dist\BigBackups.exe
    echo ============================================
    echo.
    echo Tamano del archivo:
    for %%I in (dist\BigBackups.exe) do echo    %%~zI bytes
    echo.
) else (
    echo ERROR: No se encontro el ejecutable generado
    pause
    exit /b 1
)

echo Presiona cualquier tecla para cerrar...
pause >nul
