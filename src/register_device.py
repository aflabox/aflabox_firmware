from services.registration_service import DeviceManager
import getpass

def main():
    """Main function to execute the device registration process."""
    # Create an instance of DeviceManager
    current_user = getpass.getuser()
    
    manager = DeviceManager(update_hostname=current_user!="elijahmwangi")
    
    # Register the device
    result = manager.register_device()
    
    # Display the results
    if "error" in result:
        print(f"Registration failed: {result['error']}")
    else:
        print("\nDevice Details")
        print("--------------")
        for key, value in result.items():
            print(f"{key}: {value}")
            
    # qr_image ,sizes= create_qr_on_custom_image(
    #     qr_data="https://github.com/python-pillow/Pillow",
    #     text="Code: 787654",
    #     output_path="pillow_qrcode.png"
    # )
    # qr_image.show()
   

if __name__ == "__main__":
    main()