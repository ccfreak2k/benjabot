# Configure these tables to taste.
# NOTE: Adding or removing any entry will change which responses are picked
# for a particular song title.

# Describes the song.
descriptors = [
    'That song is great!',
    'That song is _amazing_.',
    'That song is terrible!',
    'That song isn\'t very good.',
    'I hate that song.',
    'That was my favorite as a kid.',
    'That was my favorite in high school.',
    'That was my favorite in college.',
    'That\'s one of my favorite songs!',
    'It\'s got a great beat!',
    'Here\'s the thing: everyone else loves it but I really don\'t.',
    'Everyone else hates it but I think it\'s good.',
    'I was listening to this on my way to work.',
]

# Describes a chart.
charts = [
    'The {0} is really easy.',
    'The {0} is _amazing_.',
    'The {0} is pretty good.',
    'The {0} is alright.',
    'Love the {0}.',
    'I hate the {0}.',
    'The {0} is fun.',
    'The {0} is not fun.',
    'The {0} is pretty challenging.',
    'The {0} should be a {1}.',
    'The {0} is actually harder than the {1}.',
    'The {0} is actually easier than the {1}.'
]

# Extra bonus song/chart description.
extra = [
    'I hate that M run in it.',
    'I haven\'t passed it on rank yet.',
    'It\'s mostly half-doubles.',
    'There\'s a lot of bracketing in it.',
    'I have a freestyle idea for it.',
    'I wish this song was still in the game.',
    'I don\'t know why this is still in the game.',
    'I\'m close to passing that one.',
    'It took me a while to pass it.',
    'Of _course_ Shawn already SSS\'d it.',
    'I don\'t think Shawn has even passed it.',
    'Fefemz has the world record on it.',
    'The full song is uncensored.',
    'The song got censored in later games.',
    'They actually _re-added_ it after removing it.',
    'It\'s one of Crispy\'s favorite songs.',
    'This really should be in a tournament some day.',
    'I actually saw Chris4Life play that one.',
    'I _really_ wish they had the full song.',
    'I love all of the charts, but I hate the song.',
    'I hate all of the charts, but I love the song.',
    'A lot of people seem to have trouble with this one.',
    'For some reason, I have a _lot_ of trouble with this one.',
    'I want to make a {0} chart for it.',
    'They changed the background video for it.',
    'The chart just...doesn\'t work.',
    'This one is on Pump mobile!'
]

# Autoresponses to certain words or phrases.
# Key should be the regex to match, value should be the response.
autoresponses = {
    r'gu*n.?r[o0]+[ckx]+': 'STOP PLAYING GUN ROCK!',
    r'stage\s*br(eak|ake)': '_HEY!!_'
}
