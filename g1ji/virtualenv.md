## Install virtualenv
```pip install virtualenv```
****
## Create a Virtual Environment
```python -m venv env --without-pip```
****


## Activate the Virtual Environment
###### Command Prompt
```.\env\Scripts\activate```
###### PowerShell
```.\env\Scripts\Activate.ps1```
###### Git Bash
```source env/Scripts/activate```
###### Ubuntu
```source env/bin/activate```




****
## Deactivate the Virtual Environment
###### Deactivate the Virtual Environment
```deactivate```


****
## Dependencies ***(Activate the Virtual Environment first)***
###### Install Dependencies
```pip install -r requirements.txt```

###### freeze Dependencies
```pip freeze > requirements.txt```

###### Install new Dependence
```pip install <package-name> && pip freeze > requirements.txt```
