@ECHO OFF
echo %1
echo %~dp0
set name="%~dp0app.json"
move /y %1 %name%