---
id: KB-016
title: Laptop Won't Boot or Asks for a BitLocker Recovery Key
category: Hardware
tags: [boot, bitlocker, recovery-key, startup]
---

# Laptop Won't Boot or Asks for a BitLocker Recovery Key

## Symptoms
- The laptop shows a blue **BitLocker recovery** screen asking for a 48-digit recovery key.
- Nothing happens when you press the power button, or the screen stays black.
- The laptop restarts repeatedly or shows "Automatic Repair".

## Cause
All Northwind laptops are encrypted with **BitLocker**. Windows asks for the recovery key when it detects a change that could indicate tampering, such as a BIOS/firmware update, a docking station or USB device connected during startup, hardware repair, or several failed PIN attempts. A laptop that shows no signs of life usually has a drained battery or a stuck power state.

## Resolution steps: BitLocker recovery screen
1. Note the **Recovery key ID** (first 8 characters) shown on the screen.
2. On your phone or another computer, go to **https://myaccount.microsoft.com**, sign in, and select **Devices**.
3. Find your laptop (name format `NW-LT-#####`), click **View BitLocker Keys**, and match the Key ID.
4. Type the **48-digit** recovery key on the laptop (number keys only; the dashes are added automatically) and press **Enter**.
5. Once Windows starts, restart once more normally. Disconnect docks and USB drives before restarting.

If you cannot access the portal, call local **4357**. IT will verify your identity before reading the key to you. **Never share your recovery key** by email or chat, and never store it with the laptop.

## Resolution steps: laptop won't power on
1. Connect the original USB-C charger directly to the laptop (not through a dock) and wait **15 minutes**.
2. Check whether the charging light next to the port turns on.
3. Perform a hard reset: unplug the charger, hold the power button for **30 seconds**, plug the charger back in, then press power normally.
4. If you see "Automatic Repair", choose **Advanced options > Continue** to try booting again. Do **not** choose "Reset this PC" without IT guidance - it erases local data.

## When to contact IT
If the laptop still won't start, open a ticket from another device at https://help.northwind.example under **Hardware > Laptop** or call local **4357**. If the recovery screen appears more than **twice in a week**, report it so IT can check the TPM. IT can provide a **loaner laptop** the same business day from the IT depot on the 2nd floor (see KB-017).
