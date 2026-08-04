from typing import Dict, List
def process_guest_analytics(guests: List[str], hotel_tag: str | None = None) -> Dict[str, str]:
    results: Dict[str, str] = {}
    for guest in guests:
        upper_name = guest.upper()
        if hotel_tag is not None:
           results[guest] = f"{hotel_tag}: {upper_name}"
        else:
           results[guest] = upper_name

    return results
if __name__ == "__main__":
  guest_list = ["Alice", "Bob"]
  tagged_result = process_guest_analytics(guest_list, hotel_tag="Downtown")
  print("Tagged Results:", tagged_result)

  untagged_result = process_guest_analytics(guest_list)
  print("Untagged Results:", untagged_result)

