# Systemair SAVE Connect Integration
[![Home Assistant](https://img.shields.io/badge/home%20assistant-%2341BDF5.svg?style=for-the-badge&logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.com/donate/?business=2WF4WEHW6KQ4C&no_recurring=0&item_name=Buy+me+a+soda&currency_code=NOK)
[!["Buy Me A Coffee"](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/perara)


## Installation

### Option 1: HACS
Under HACS -> Integrations, select `+`, search for `systemair`, and install.

### Option 2: MANUALLY
```bash
cd YOUR_HASS_CONFIG_DIRECTORY    # same place as configuration.yaml
mkdir -p custom_components/systemair
cd custom_components/systemair
unzip systemair-X.Y.Z.zip
mv systemair-X.Y.Z/custom_components/systemair/* .  
```

## Usage
Configure the ventilation unit using the webui. For the SAVE Connect integration to work, you need to register an account at https://homesolutions.systemair.com/ and add the ventilation unit to the newly created user.

## Current Support
* Binary Warning/Error sensors
* Ventilation Fan Adjustment
* Sensor Reading
