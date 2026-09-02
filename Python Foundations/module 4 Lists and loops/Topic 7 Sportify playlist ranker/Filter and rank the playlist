songs = []
counts = []
while True:
    song = input("Enter the songs(enter done to stop)")
    if song == "done":
        break
    count = int(input("Enter the sons play count"))
    songs.append(song)
    counts.append(count)
print(len(songs))

threshold = int(input("Enter the playcounts threshold"))
filtered_songs = []
filtered_counts = []

for i in range(len(songs)):
    if counts[i] >= threshold:
        filtered_songs.append(songs[i])
        filtered_counts.append(counts[i])
paired = list(zip(filtered_counts, filtered_songs))
ranked = sorted(paired, reverse=True)
for rank, (count, name) in enumerate(ranked, 1):
    print(f"{rank}. {name} - {count} plays")
passed = len(filtered_songs)
removed = len(songs) - passed
print(f"{passed} songs passed the filter; {removed} were removed.")