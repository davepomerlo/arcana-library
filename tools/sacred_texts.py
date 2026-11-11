"""Classify the titles of the Internet Sacred Text Archive (sacred-texts.com).

The title list lives in data/sacred-texts-titles.txt (one title per line).
Each title gets a subject and, where one fits, the Arcana Library section it belongs to.
Rules are tried in order, so put the most specific first. Titles no rule catches can be
placed by hand in OVERRIDES.

Run it on its own to see the counts and anything still unclassified:
    python3 tools/sacred_texts.py
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
TITLES = ROOT / "data" / "sacred-texts-titles.txt"

# subject → (section slug or "", short description, sacred-texts subject page if verified)
SUBJECTS = {
    "Extraterrestrial life & UFOs": ("extraterrestrial", "Other worlds, Mars, flying saucers and contact claims.", "https://sacred-texts.com/ufo/index.htm"),
    "Atlantis, Lemuria & lost lands": ("paranormal", "Lost continents and the books that made them famous.", ""),
    "Hollow earth & alternative cosmologies": ("paranormal", "Inner worlds, flat earths and other rejected cosmologies.", ""),
    "Fortean & psychical research": ("paranormal", "Charles Fort, telepathy, clairvoyance and early psychical research.", ""),
    "Prophecy & Nostradamus": ("paranormal", "Seers, oracles and prophecies.", ""),
    "Earth mysteries": ("paranormal", "Stone circles, pyramids, mazes and ancient sites.", ""),
    "Vampires, monsters & strange creatures": ("paranormal", "Vampires, werewolves, dragons, unicorns and other creatures.", ""),
    "Bibles in other languages": ("ancient-sacred", "The Bible in some fifty languages.", ""),
    "Bible & commentaries": ("ancient-sacred", "English Bibles, concordances and commentaries.", ""),
    "Christianity": ("ancient-sacred", "Church Fathers, creeds, saints, mystics and reformers.", ""),
    "Gnosticism & apocrypha": ("esoteric", "Gnostic gospels, Enoch, the lost books and apocrypha.", ""),
    "Judaism": ("ancient-sacred", "Talmud, Midrash, liturgy and Jewish thought.", ""),
    "Kabbalah": ("esoteric", "Sefer Yetzirah, the Zohar and Kabbalistic studies.", ""),
    "Islam & Sufism": ("ancient-sacred", "Qur'an, hadith, Sufi poetry and Islamic philosophy.", ""),
    "Bahá'í Faith": ("ancient-sacred", "Writings of the Báb, Bahá'u'lláh, 'Abdu'l-Bahá and Shoghi Effendi.", ""),
    "Zoroastrianism": ("ancient-sacred", "The Avesta and Pahlavi texts.", ""),
    "Hinduism & yoga": ("ancient-sacred", "Vedas, Upanishads, epics, Puranas, Tantra and yoga.", ""),
    "Buddhism": ("ancient-sacred", "Pali suttas, Mahāyāna sūtras, Zen, Pure Land and Tibetan Buddhism.", ""),
    "Jainism": ("ancient-sacred", "Jain sūtras and teachings.", ""),
    "Sikhism": ("ancient-sacred", "The Guru Granth Sahib and Sikh history.", ""),
    "Confucianism": ("ancient-sacred", "The Confucian classics.", ""),
    "Taoism": ("ancient-sacred", "The Tao te ching, Zhuangzi, Liezi and Taoist texts.", ""),
    "Shinto & Japan": ("ancient-sacred", "Kojiki, Nihongi, Shinto ritual and Japanese literature.", ""),
    "Asia & Siberia: myth and folklore": ("ancient-sacred", "China, Korea, Tibet, Siberia, the Ainu and more.", ""),
    "Ancient Egypt": ("ancient-sacred", "The Book of the Dead, Pyramid Texts and Egyptian religion.", ""),
    "Ancient Near East": ("ancient-sacred", "Babylonian, Assyrian, Sumerian and Hittite texts.", ""),
    "Classical myth & literature": ("ancient-sacred", "Homer, Hesiod, the tragedians and Greek and Roman religion.", "https://sacred-texts.com/cla/index.htm"),
    "Classical philosophy": ("philosophy", "Plato, Aristotle, the Stoics, Epicureans and Neoplatonists.", ""),
    "Celtic": ("ancient-sacred", "Irish, Welsh, Scottish, Breton and Manx myth and folklore.", ""),
    "Norse & Germanic": ("ancient-sacred", "The Eddas, sagas and Germanic legend.", ""),
    "Native American": ("ancient-sacred", "Myths, rituals and texts of the peoples of the Americas.", ""),
    "Africa & the African diaspora": ("ancient-sacred", "African myth and folklore, and the religions of the diaspora.", ""),
    "Pacific & Australia": ("ancient-sacred", "Hawaiian, Māori, Polynesian and Aboriginal Australian traditions.", ""),
    "European folklore & fairy tales": ("ancient-sacred", "Fairy books, folk tales and folklore from across Europe.", ""),
    "Hermeticism & alchemy": ("esoteric", "The Hermetica and the alchemical classics.", ""),
    "Magic & grimoires": ("esoteric", "Ceremonial magic, grimoires and folk magic.", ""),
    "Tarot, astrology & divination": ("esoteric", "Tarot, astrology, numerology and fortune-telling.", ""),
    "Freemasonry & secret societies": ("esoteric", "Masonic ritual, Rosicrucians, Templars and the Illuminati.", ""),
    "Theosophy & occultism": ("esoteric", "Blavatsky, Steiner and the Western occult revival.", ""),
    "New Thought": ("esoteric", "Mental science, the power of mind and prosperity teaching.", ""),
    "Swedenborg": ("esoteric", "The theological and visionary works of Emanuel Swedenborg.", "https://sacred-texts.com/swd/eiu/eiu00.htm"),
    "Mysticism": ("esoteric", "Christian, Islamic and comparative mysticism.", ""),
    "Witchcraft & neopaganism": ("esoteric", "Witch trials, the witch-cult theory and modern paganism.", ""),
    "Sacred sexuality": ("esoteric", "Love manuals, phallic worship and sexual mysticism.", ""),
    "New religious movements": ("esoteric", "Mormonism, Oahspe, Rastafari, Discordianism and other movements.", ""),
    "Philosophy (modern)": ("philosophy", "Descartes to Nietzsche.", ""),
    "Age of Reason & freethought": ("philosophy", "Paine, Ingersoll, Twain and religious criticism.", ""),
    "Comparative religion & anthropology": ("", "Frazer, Max Müller and the early study of religion.", ""),
    "Utopias & speculative fiction": ("", "Utopias, dystopias and early science fiction.", ""),
    "Shakespeare": ("", "The plays and poems.", ""),
    "Literature & poetry": ("", "Epics, romances, poetry and other literature.", ""),
    "Women & gender": ("", "Women's history, rights and religion.", ""),
    "Other": ("", "Titles not yet placed in a subject.", ""),
}

SHAKESPEARE = {
    "All's Well That Ends Well", "Antony and Cleopatra", "As You Like It", "Comedy of Errors", "Coriolanus",
    "Cymbeline", "Hamlet", "Julius Caesar", "King John", "King Lear", "Lovers' Complaint, A", "Love's Labour's Lost",
    "Macbeth", "Measure for Measure", "Merchant of Venice", "Merry Wives of Windsor", "Midsummer Night's Dream",
    "Much Ado About Nothing", "Othello", "Pericles, Prince of Tyre", "Rape of Lucrece", "Romeo and Juliet",
    "Sonnets", "Taming of the Shrew", "Tempest", "Timon of Athens", "Titus Andronicus", "Troilus and Cressida",
    "Twelfth Night", "Two Gentlemen of Verona", "King Henry the Eighth", "King Henry the Fifth", "King Henry the Fourth, Part I", "King Henry the Fourth, Part II", "King Henry the Sixth, Part I", "King Henry the Sixth, Part II", "King Henry the Sixth, Part III", "King Richard the Second", "King Richard the Third", "Two Noble Kinsmen", "Venus and Adonis", "Winter's Tale, The",
}
PLATO_ETC = {
    "Apology (the Death of Socrates)", "Charmides, or Temperance", "Cratylus", "Critias", "Crito", "Euthydemus",
    "Euthyphro", "Gorgias", "Ion", "Laches or Courage", "Laws", "Lysis, or Friendship", "Meno", "Parmenides",
    "Phaedo", "Phaedrus", "Philebus", "Protagoras", "Seventh Letter, The", "Sophist", "Statesman", "Symposium",
    "Theaetetus", "Timaeus", "Poetics", "Politics", "On The Heavens", "On Generation and Corruption",
    "Nicomachean Ethics, The", "Meditations", "Discourses of Epictetus, The", "Enchiridion, The",
    "Letter to Menoeceus", "On The Nature Of Things", "Enneads of Plotinus, The", "Ancilla to the Pre-Socratic Philosophers",
    "Golden Verses of Pythagoras, The", "Fragments that Remain of the Lost Writings of Proclus",
    "Two Orations of the Emperor Julian", "Sand Reckoner, The",
}
GREEK_DRAMA = {
    "Agamemnon", "Ajax", "Alcestis", "Andromache", "Antigone", "Bacchantes, The", "Choephori (Libation Bearers), The",
    "Cyclops, The", "Electra", "Hecuba", "Helen", "Heracleidae, The", "Heracles", "Hippolytus", "Iphigenia At Aulis",
    "Iphigenia in Tauris", "Medea", "Oedipus at Colonus", "Oedipus the King (Oedipus Rex)", "Orestes", "Persians, The",
    "Philoctetes", "Phoenissae, The", "Prometheus Bound", "Rhesus", "Seven Against Thebes, The", "Suppliants, The",
    "Trachiniae, The", "Trojan Women, The",
}

# ordered (subject, regex) rules
RULES = [
    ("Extraterrestrial life & UFOs", r"\bMars\b|Flying Saucers|Secret of the Saucers|Space People|Other Tongues|Earths in the Universe|War of the Worlds|Dweller on Two Planets|True Story: Parallel|Closed World to the Infinite|Book of Earths"),
    ("Atlantis, Lemuria & lost lands", r"Atlant|Lemuria|\bMu\b|Lost Continent|Oera Linda|Selestor"),
    ("Hollow earth & alternative cosmologies", r"Earth's Core|Pellucidar|Earth's Interior|Center of the Earth|Smoky God|Phantom of the Poles|Symzonia|Cellular Cosmogony|Zetetic|Etidorhpa|Paradise Found|Sacred Theory of the Earth|Theory of the Earth|Vril"),
    ("Fortean & psychical research", r"Book of the Damned|New Lands|Wild Talents|\bLo!|Extra-Sensory|Mental Radio|Clairvoyance|Human Atmosphere|Psychic Phenomena|Abominable Snowmen|Coming of the Fairies|Know Your Magnetic Field|Wanderer in the Spirit Lands|Spirit Lands|Atom-Smashing|Secret Science Behind Miracles"),
    ("Prophecy & Nostradamus", r"Nostradamus|Prophecies of|Mother Shipton|Brahan Seer|Sibylline|Examination Of The Prophecies"),
    ("Earth mysteries", r"Stonehenge|Pyramid(?! Texts)|Mazes|Trackways|Tower Legends|Architecture, Mysticism"),
    ("Vampires, monsters & strange creatures", r"Vampir|Were-Wolves|Dracula|Lair of the White Worm|Dragon|Unicorn|Mythical Monsters|Fictitious and Symbolic Creatures"),
    ("Bibles in other languages", r"^(Afrikaans|Albanian|Amharic|Arabic|Aramaic|Basque|Breton|Chamorro|Chinese Union|Coptic|Croatian|Danish|Dutch|Eastern Armenian|Esperanto|Estonian|Finnish|French|Georgian|German|Gothic|Hungarian|Italian|Kabyle|Korean|Latvian|Manx|Maori|Modern Hebrew|Norwegian|Portuguese|Potawatomi|Romani|Russian|Scottish Gaelic|Spanish|Swahili|Swedish|Tagalog|Turkish|Ukrainian|Vietnamese|Western Armenian|Wolof|Xhosa) Bible|Polyglot Bible"),
    ("Swedenborg", r"Arcana Coelestia|Apocalypse (Explained|Revealed)|Heaven and Hell|Conjugial Love|Divine Love|Divine Providence|Divine Wisdom|De (Conjugio|Domino|Verbo)|Doctrine of (Faith|Life|Sacred Scriptures|the Lord)|Last Judgment|New Jerusalem|True Christian Religion|Spiritual Diary|Interaction of the Soul|Invitation to the New Church|Gist of Swedenborg|Brief Exposition|^Charity$|Canons|Correspondence"),
    ("Gnosticism & apocrypha", r"Gnos|Pistis Sophia|Enoch|Jubilees|Jasher|Giants|Lost Books|Forgotten Books|Apocryph|Pseudepigrapha|Adam and Eve|Cave of Treasures|Book of the Bee|Gospel of (Thomas|Mary|Barnabas)|Biblical Antiquities of Philo|Fragments of a Faith Forgotten|Hymn of Jesus|Unknown Life of Jesus|Aquarian Gospel|Jesus An Essene|Excerpts from the Gospel"),
    ("Bible & commentaries", r"\bBible\b|Testament|Septuagint|Vulgate|Tanakh|King James|Concordance|Commentary|Notes on the|Scofield|Easton|Vincent's Word|Treasury of (David|Scriptural)|Exposition of the Entire|^(Acts|Corinthians|Daniel|Ezekiel|Galatians|Genesis|Hebrews|Hosea|Isaiah|Jeremiah|Joel|John|Jonah|Joshua|Matthew|Philippians|Psalms|Romans|Timothy|Zechariah|Catholic Epistles|Prophets and Psalms|Harmony of the Law)|Book of Revelation|Synopsis of the Books|Bible Maps|Young's Literal|Douay|Darby|Webster's|American Standard|Weymouth|People's New Testament|Explanatory Notes|Geneva Bible|Legends of Genesis|Biography of the Bible|Human Nature in the Bible|Woman's Bible"),
    ("Kabbalah", r"Kabbal|Qabalah|Cabala|Zohar|Sepher Ye"),
    ("Judaism", r"Talmud|Mishna|Midrash|Jewish|Judaism|Rabbi|Haggad|Pirqe Aboth|Jewish Fathers|Maimonides|Guide for the Perplexed|Kitab al Khazari|Gabirol|Hebraic|Medieval Hebrew|Tractate|Ecclesiasticus|Legends of the Jews|Kaplan|Schechter|Ancient Jewish|Philistines|Prolegomena to the History of Ancient Israel"),
    ("Bahá'í Faith", r"Baha|Bab\b|Abdu'l|Guardian|Kitab-i|Dawn Breakers|Hidden Words|Seven Valleys|Epistle to the Son of the Wolf|God Passes By|Promised Day|Advent of Divine Justice|Citadel of Faith|Unfolding Destiny|Paris Talks|Some Answered Questions|Tablets? |Foundations of World Unity|Promulgation of Universal Peace|Secret of Divine Civilization|Traveller's Narrative|Memorials of the Faithful|Prosperity of Humankind|Promise of World Peace|Light of Divine Guidance|High Endeavours|Messages to America|Arohanui|Directives from|World Order|Will and Testament|Prayers and Meditations|Tablet to August Forel"),
    ("Islam & Sufism", r"Qur|Koran|Hadith|Islam|Muslim|Sufi|Masnavi|Mesnevi|Rubaiyat|Hafiz|Sadi|Gulistan|Bustan|Mishk|Imam|Karbala|Shia|Kumayl|Abu Hamzah|Druze|Alawite|Alfarabi|Arabian|Arabic Thought|Bird Parliament|Salaman and Absal|Enclosed Garden|Secret Rose Garden|Secrets of the Self|Diwan|Afghans|Maqámát|Ulema|Christ In Islâm|Kasîdah|Alchemy of Happiness|1001|Hanged Poems|Shah Namah|Baghdad"),
    ("Zoroastrianism", r"Zend Avesta|Pahlavi|Zarathustra(?!$)|Zoroaster|Yatkar|Zarir"),
    ("Jainism", r"Jain|Five Great Vows|Fourteen Auspicious|Nine Tattvas|Six Universal Substances|Ten Virtues Of Monks|Twelve Vows|Twelve Reflections|Ashta Prakari|Five Bodies"),
    ("Sikhism", r"Sikh|Guru Granth"),
    ("Buddhism", r"Buddh|Dhammapada|Sutta|Jataka|Mahâyâna|Mahayana|Lotus Sutra|Saddharma|Milinda|Vinaya|Udâna|Zen|Gateless Gate|Amitabha|Pure Land|Shinran|Ashvagosha|Açvaghosha|Fo-Sho-Hing|Psalms of the Sisters|Way to Nirvana|Dialogues of the Buddha|Smokey the Bear|Tibet|She-rab|Tilak"),
    ("Hinduism & yoga", r"(?i:veda|vedic|vedânt)|Upanishad|Gita|Bhagavad|Mahabharata|Ramayana|Purana|Manu\b|Brahman|Brahma|Sutras of Patanjali|Yoga|Yogi|Tantra|Kali|Kâlî|Shakti|Devî|Grihya|Vishnu|Sacred Laws of the Âryas|Satapatha|Sankaracharya|Crest-Jewel|Ramakrishna|Raja Yoga|Karma-Yoga|Kundalini|Science of Breath|Hindu|Sanskrit|Kalidasa|Little Clay Cart|Prem Sagur|Vemana|Hymns to the Goddess|Dakshinamurti|Minor Law Books|Black Marigolds|Gitanjali|Fruit-Gathering|Crescent Moon|Stray Birds|Sadhana|Home and the World|Songs of Kabîr|Indian Idylls|Old Deccan|Occult Science in India|Vikram|Twenty-two Goblins|Shaman, Saiva|Kama Sutra|Ananga Ranga|Hatha"),
    ("Confucianism", r"Confuci|Analects|Mencius|Doctrine Of The Mean|Great Learning|Filial|Book of Odes|Book of Poetry"),
    ("Taoism", r"Tao|Lao ?Tzu|Laotzu|Lieh-Tz|Yang Chu|Kan-Ying|Yin Chih|Canon of Reason|Musings of a Chinese Mystic|Kung-Fu"),
    ("Shinto & Japan", r"Kojiki|Nihongi|Kogoshui|Yengishiki|Shinto|Japan|Bushido|Genji|Nō Plays|Kwaidan|In Ghostly Japan|Gleanings In Buddha-Fields|Hundred Verses|Haiku|Shundai|Creed of Half Japan|Book of Tea|Ideals of the East|Pale Ink"),
    ("Asia & Siberia: myth and folklore", r"China|Chinese|Feng Shui|Ssuma|Korea|Siberia|Chukchee|Koryak|Yukaghir|Ainu|Aino|Kutune|Yukara|Armenian|Georgian|Man in the Panther|Feast of Lanterns|Sacred Places in China|Andamans|Philippine|Oriental"),
    ("Ancient Egypt", r"Egypt|Pyramid Texts|Isis|Osiri|Hieroglyphics of Horapollo|Tutankhamen|Funerary Offerings|Stolen Legacy|Wisdom of the Egyptians"),
    ("Ancient Near East", r"Babylon|Assyria|Chaldean|Chaldæan|Gilgam|Izdubar|Ishtar|Enuma|Seven Tablets|Sumerian|Hammurabi|Adapa|Seven Evil Spirits|Records of the Past|Syrian Goddess|Yezid|Yezeed|Mithra"),
    ("Classical philosophy", r"Plotinus|Pythagoras|Epictetus|Proclus|Socrates|Pre-Socratic"),
    ("Classical myth & literature", r"Homer|Iliad|Odyss|Hesiod|Theogony|Works and Days|Aeneid|Virgil|Eclogues|Georgics|Argonautica|Epic Cycle|Aethiopis|Cypria|Little Iliad|Sack of Ilium|Ovid|Metamorphoses|Sappho|Apollonius|Golden Asse|Cupid and Psyche|Lucian|Herodotus|Tacitus|Josephus|Caesar|Petronius|Procopius|Plutarch|Orpheus|Eleusinian|Greek|Greece|Rome|Roman|Amazons|Aphrodite|Priapeia|Mimes of the Courtesans|Coronis|Ioläus|Euripides|Mycenaean|Crete|Delphic|Etruscan|Frogs and Mice|Bilitis|Contest of Homer|Lives of the Greek Heroines|Adventures of Odysseus|Heroes, or Greek"),
    ("Celtic", r"Celt|Irish|Ireland|Druid|Welsh|Wales|Barddas|Gododdin|Mabinogion|Ossian|Carmina Gadelica|Cuchulain|Táin|Mag Tuired|Dá Derga|Bran|Scottish|Scotland|West Highlands|Brittany|Breton|Isle of Man|Manx|Phynodderree|Cornwall|West of England|Aran Islands|Wicklow|Beside the Fire|Gods and Fighting Men|King of Ireland|Crock of Gold|Candle of Vision|In The Seven Woods|Later Poems|Feuds of the Clans|Secret Common-Wealth|Arthur|Round Table|Graal|Morte|Vita Merlini|Geoffrey of Monmouth|Merlin|Cliges|Erec|Dartmoor|Pixies|British Goblins|Champions of the Round"),
    ("Norse & Germanic", r"Edda|Saga|Norse|Norway|Odin|Volsung|Nibelung|Niblung|Heimskringla|Beowulf|Anglo-Saxon|Teutonic|Ragnarok|Danish History|Njal|Grettir|Egil|Gisli|Viga-Glum|Laxdaela|Orkney|Rhine|Wolfings|Cormac|Esthonia|Kalevala|Baltic"),
    ("Native American", r"Indian|Navaho|Navajo|Zuñi|Hopi|Cherokee|Iroquo|Algonquin|Blackfoot|Apache|Pima|Aw-aw-tam|Maidu|Miwok|Hupa|Yana|Coos|Chinook|Tlingit|Tsimshian|Haida|Kwakiutl|Achomawi|Diegueño|Luiseño|Cahuilla|Shoshon|Seneca|Omaha|Oglala|Dakota|Acoma|Cochiti|Tewa|Pueblo|Yosemite|Chinigchinich|Tauquitch|Chaup|Kâ'-kâ|Mission Indians|Mission Record|Walam Olum|Handsome Lake|Popol|Chilam Balam|Maya|Aztec|Rig Veda Americanus|Yncas|Inca|Viracocha|Ollantay|Pachacuti|Mexico and Peru|Yucatan|Guiana|Eskimo|Old North Trail|Thirty-Fifth Parallel|Thunder Bird|Tootooch|Many Swans|Corn|Spider Woman|Noqoìlpi|Yaqui|Pomo|Peyote|Delight Makers|Tejas|Path on the Rainbow|Soul of the Indian|Web of Indian Life|Fusang|Norse Discovery of America|Creation Myths of Primitive America|Coffee in the Gourd|Storm God|Truth of a Hopi|Tenderfoot|Lore and the Lure|Legend of Tauquitch|Clowns, Priests"),
    ("Africa & the African diaspora", r"Africa|Nigeria|Yoruba|Ífè|Hausa|Bantu|Bushman|Kaffir|Xhosa|Fjort|Fetichism|Black Man's Mind|Negro|Anansi|Jamaica|Voodoo|Voudoo|Obeah|Drums and Shadows|New Orleans|Kebra Nagast|Ethiopians|Cushite|Rastafari|Holy Piby|Black Supremacy"),
    ("Pacific & Australia", r"Hawai|Kumulipo|Maui|Maori|Whare-Wananga|Polynesia|Oceanic|Samoan|Easter Island|Te Pito|Australia|Aborigin|Euahlayi|Northern Territory|Trobriand|Baloma|Noa Noa"),
    ("Hermeticism & alchemy", r"Hermes|Hermetic|Pymander|Emerald Tablet|Corpus Hermeticum|Virgin of the World|Alchem|Tincture|Antimony|Philosophers|Turba|Collectanea Chemica|Eudoxus|Coelum philosophorum|Mirror of Alchemy|Glory of the World|Golden Chain|Treasure of Treasures|Freher|Philadelphian Gold|Mary the Prophetess|Hortulanus|Stone of the Philosophers"),
    ("Magic & grimoires", r"Magic|Magick|Grimoire|Key of Solomon|Abramelin|Book of Moses|Calls of Enoch|Demotic Magical|Magus|Talismans|Pow-wows|Evil Eye|Horse-Shoes|Taboo, Magic|Ancient Art and Ritual|Baltic Wizards"),
    ("Tarot, astrology & divination", r"Tarot|Astrolog|Tetrabiblos|Stars|Solar Biology|Astro-Diagnosis|Fortune|Numbers, Their Occult|Gypsy Sorcery|Sun Lore|Moon Lore|Zodiac"),
    ("Freemasonry & secret societies", r"(?i:mason)|Ahiman Rezon|Templar|Illuminati|Rosicruci|Secret Societies|Dionysian Artificers|Builders|Brother of the Third Degree|Proofs of a Conspiracy|Comte de|Trinosophia|Morals and Dogma|Shibboleth|Monitor|Secret Teachings of All Ages|With the Adepts|Cloud Upon the Sanctuary|Hidden Church|Zanoni"),
    ("Theosophy & occultism", r"Theosoph|Secret Doctrine|Isis Unveiled|Dzyan|Initiation|Initiate|Knowledge of the Higher Worlds|Tertium Organum|Eternal Career|Max Heindel|Unveiled Mysteries|I AM|Pronaos|Gleanings of a Mystic|Consciousness of the Atom|Message of the Stars|Teachings of An Initiate|Clothed With The Sun|Burden of Isis|Way of Power|Ancient and Modern Initiation|Hidden Power"),
    ("New Thought", r"Mental Science|Mind Cure|Creative Mind|Dynamic Thought|In Tune with the Infinite|Master Key|Science of Mind|Science of Getting Rich|Secret of the Ages|Secret Door To Success|Game of Life|Your Word Is Your Wand|Think and Grow Rich|Prosperity|Lessons in Truth|Talks on Truth|Twelve Powers|Christian Healing|Jesus Christ Heals|Keep a True Lent|Teach Us to Pray|Myrtle Fillmore|Mysteries of (Genesis|John)|Self-Suggestion|Your Forces|Law and the Word|Quimby|Science and Health|Facing Life|Life and Its Mysteries|Seeming Unreality|Secret of the Universe|What All the World's|Thought Relics|Atom-Smashing|Love and Death"),
    ("Mysticism", r"Mystic|Cloud of Unknowing|Interior Castle|Imitation of Christ|Spiritual Marriage|Cherubinic|Signature of All Things|Cosmic Consciousness|Aurora|Dionysius the Areopagite|Varieties of Religious Experience|Fountain of Life|Spiritual Life"),
    ("Witchcraft & neopaganism", r"Witch|Aradia|Book of Shadows|Malleus|Dæmonology|Demonology|Devil|Loudun|Sorceress|Pagan|Golden Bough|Margaret Murray|Book of the Goddess|Principia Discordia|Temporary Autonomous|Hallowe'en|Christmas in Ritual|Festivals of Western|Festival of The Sun"),
    ("Sacred sexuality", r"Phallic|Priapus|Generative|Sex Worship|Karezza|Male Continence|Perfumed Garden|Love Books|Serpent|Ophiolatreia|Love's Coming of Age|Intermediate Types|Problem in (Greek|Modern) Ethics|Woman's Mysteries"),
    ("New religious movements", r"Mormon|Latter-Day|Doctrine and Covenants|Pearl of Great Price|Book of Abraham|Utah|Oahspe|Mankind United|Great Controversy|Smokey|Communistic Societies|Amish|Mennonite|Shakers?"),
    ("Philosophy (modern)", r"Critique|Metaphysic|Kant|Discourse on the Method|Meditations on First|Monadology|Ethica|^Ethics$|Leviathan|Hylas|Principles of Human Knowledge|Enquiry Concerning|Hume|Of (Essay|Superstition|Tragedy|the (Delicacy|Liberty|Rise|Standard))|Natural History of Religion|Dialogues Concerning|Essays on Suicide|On Liberty|Utilitarianism|Representative Government|Subjection of Women|Theologico-Political|On the Improvement of Understanding|Science of Right|Pensees|Provincial Letters|Thus Spake|Art of Worldly Wisdom|Art of War|Essays, (First|Second)|Transcendentalist|Walden|Civil Disobedience|Life Without Principle|Slavery in Massachusetts|Plea for Captain|Prolegomena to Any"),
    ("Age of Reason & freethought", r"Age of Reason|Common Sense|Rights of Man|Absurdities|Self-Contradictions|Biblical Blasphemy|Why I Am An Agnostic|Letters From The Earth|What is Man|War Prayer|Abortion in the Bible|Roe v\. Wade|Jefferson Bible|Thou Shalt Not Kill|Sixteen Crucified|Pagan Christs|Bible, The Koran"),
    ("Comparative religion & anthropology", r"Animism|Religion and Myth|Comparative|Migration of Symbols|Bygone Beliefs|Superstitions and Customs|Manners, Customs|Myth of the Birth of the Hero|Science of Fairy Tales|Study of Fairy Tales|Tom Tit Tot|Grateful Dead|Remarks on Shamanism|Shamanism|Folk-Lore of Women|Origin of Species|Descent of Man|Voyage of the Beagle|Funeral Customs|Oriental Religions|Astrology and Religion|Prolegomena to the Study of Greek Religion|From Ritual To Romance|Survivals in Belief|Religious Cults Associated|India in Primitive Christianity|Timeline|Sacred Texts Timeline|Orpheus, Myths"),
    ("Utopias & speculative fiction", r"Utopia|Atlantis, The New|New Atlantis|City of the Sun|Erewhon|News from Nowhere|Herland|Iron Heel|Caesar's Column|Cæsar's Column|Angel of the Prairies|In Days To Come|Garden Cities|Frankenstein|Vampyre|Golden Mountain|Modern Utopia|Wandering Host|Sundering Flood|Glittering Plain|Water of the Wondrous Isles|Wood Beyond the World|Well at the World's End|Hollow Land|Child Christopher|House of the Wolfings|Worm Ouroboros|Dunsany|Pegana|Time and the Gods|Sword of Welleran|Dreamer's Tales|Fifty-One Tales|Book of Wonder$|Tales of Wonder|Plays of Gods and Men|Don Rodriguez|First 1000 lines"),
    ("European folklore & fairy tales", r"Fairy|Fairies|Folk|Fables|Legends and Romances|Legends and Popular|Basque|Russian|Slavonic|Czech|Roumanian|Turkish|Gipsies|Gypsy|Servia|Spain|Pennsylvania Germans|Noodles|Popular Tales|Book of Saints and Wonders|Nature Myths|Robin Hood|English and Scottish Popular Ballads|Old English Ballads|Earthly Paradise|Lusiad|Song of Roland|Lay of the Cid|Orlando|Igor|Sports and Pastimes|Stories of the Months|Hero-Myths|Wonder Tales|Holy Land|Grimm"),
]
OVERRIDES = {
    "Book of Wonder (Episcopal), The": "Christianity",
    "Book of Common Prayer, The": "Christianity",
    "Atlantida (L'Atlantide)": "Atlantis, Lemuria & lost lands",
    "Book of Knowledge": "Theosophy & occultism",
    "Book of Folklore, A": "European folklore & fairy tales",
    "Book of the Damned": "Fortean & psychical research",
    "Book of Earths, The": "Earth mysteries",
    "Shepherd And The Daughter Of The Sun, The": "Native American",
    "Women": "Women & gender",
    "Woman and the New Race": "Women & gender",
    "Woman, Church, and State": "Women & gender",
    "Woman's Bible, The": "Women & gender",
    "Vindication of the Rights Of Woman": "Women & gender",
    "Subjection of Women, The": "Women & gender",
    "Lives of the Greek Heroines": "Women & gender",
    "Folk-Lore of Women": "Women & gender",
    "Bible, The Koran, and the Talmud, The": "Age of Reason & freethought",
    "Divine Comedy, The": "Literature & poetry",
    "Paradise Lost, Paradise Regained": "Literature & poetry",
    "Faerie Queene, The": "Literature & poetry",
    "Stories from the Faerie Queene": "Literature & poetry",
    "Canterbury Tales and Other Works of Chaucer (Middle English), The": "Literature & poetry",
    "Tales from Chaucer": "Literature & poetry",
    "Idylls of the King, The": "Literature & poetry",
    "Songs of Innocence and of Experience": "Literature & poetry",
    "Christmas Carol, A": "Literature & poetry",
    "Visit from St. Nicholas, A": "Literature & poetry",
    "Fifty Christmas Poems for Children": "Literature & poetry",
    "Wagner's Ring of the Niblung": "Norse & Germanic",
    "Da Vinci Notebooks, The": "Literature & poetry",
    "Forty Modern Fables": "Literature & poetry",
    "Fly, The": "Literature & poetry",
    "White Horse": "Literature & poetry",
    "My Own Life": "Philosophy (modern)",
    "Famous Men of the Middle Ages": "Literature & poetry",
    "Address to the Nobility": "Christianity",
    "Martin Luther's 95 Theses": "Christianity",
    "Love Letters of Abelard and Heloise, The": "Christianity",
    "Story of My Misfortunes: The Autobiography of Peter Abelard, The": "Christianity",
    "Summa Theologica": "Christianity",
    "Works of St. Anselm": "Christianity",
    "Confessions of Saint Augustine, The": "Christianity",
    "Political Aspects of S. Augustine's 'City of God', The": "Christianity",
    "Mythology of the Mission Indians": "Native American",
    "Shaman, Saiva and Sufi": "Islam & Sufism",
    "Sufi Message of Spiritual Liberty, A": "Islam & Sufism",
    "Kalevala (English), The": "Norse & Germanic",
    "Kalevala (Finnish), The": "Norse & Germanic",
    "Hero of Esthonia, The": "Norse & Germanic",
    "Tales of the Enchanted Islands of the Atlantic": "Atlantis, Lemuria & lost lands",
    "Paradise Found": "Hollow earth & alternative cosmologies",
    "Garden of Eden; or The Paradise Lost & Found, The": "Hollow earth & alternative cosmologies",
    "Twenty-two Goblins": "Hinduism & yoga",
    "Book of Talismans, Amulets and Zodiacal Gems, The": "Magic & grimoires",
    "Mythology of the Diegueños, The": "Native American",
    "Architecture, Mysticism and Myth": "Earth mysteries",
    "Ancient Fragments": "Ancient Near East",
    "Life of Apollonius of Tyana, The": "Classical philosophy",
    "Epistles of Apollonius of Tyana, The": "Classical philosophy",
    "Treatise of Eusebius Against the Life of Apollonius by Philostratus, The": "Classical philosophy",
    "Apollonius of Tyana": "Classical philosophy",
    "Plutarch's Morals: Theosophical Essays": "Classical philosophy",
    "De Iside et Osiride": "Ancient Egypt",
    "Thrice-Greatest Hermes, Vol. 1": "Hermeticism & alchemy",
    "Thrice-Greatest Hermes, Vol. 2": "Hermeticism & alchemy",
    "Thrice-Greatest Hermes, Vol. 3": "Hermeticism & alchemy",
    "Hymns of Orpheus, The": "Classical myth & literature",
    "Thus Spake Zarathustra": "Philosophy (modern)",
    "Chaldæan Oracles of Zoroaster, The": "Hermeticism & alchemy",
    "Code of the Illuminati": "Freemasonry & secret societies",
    "Secret Societies of the Middle Ages": "Freemasonry & secret societies",
    "Christian Topography": "Hollow earth & alternative cosmologies",
    "Saddharma-pundarîka (The Lotus Sutra) (SBE 21)": "Buddhism",
    "Tibetan Folk Tales": "Buddhism",
    "Sacred Books of the East, Volume 3": "Confucianism",
    "Sacred Books of the East, Volume 16": "Confucianism",
    "Sacred Books of the East, Volume 27": "Confucianism",
    "Sacred Books of the East, Volume 28": "Confucianism",
    "Vol. II: The Descent of the Sun": "Hinduism & yoga",
    "Vol. III: A Heifer of the Dawn": "Hinduism & yoga",
    "Vol. IV: In the Great God's Hair": "Hinduism & yoga",
    "Volume I: Lectures": "Swedenborg",
    "Volume II: Lectures": "Swedenborg",
    "Correspondence": "Swedenborg",
    "Canons": "Swedenborg",
    "Scholarship": "Bahá'í Faith",
    "Peace": "Bahá'í Faith",
    "Historic Lecture": "Bahá'í Faith",
    "Great March, The": "Christianity",
    "Mission Memories": "Native American",
    "Japan Will Turn Ablaze": "Bahá'í Faith",
    "Tutankhamen: Amenism, Atenism and Egyptian Monotheism": "Ancient Egypt",
    "Legends of the Gods: The Egyptian Texts": "Ancient Egypt",
    "Islam": "Islam & Sufism",
    "Golden Verses of Pythagoras, The": "Classical philosophy",
    "Kung-Fu, or Tauist Medical Gymnastics": "Taoism",
    "Unicode Qur'an": "Islam & Sufism",
    "Gospel of Ramakrishna, The": "Hinduism & yoga",
    "Laughable Stories of Bar-Hebraeus, The": "Christianity",
    "Story of Utopias, The": "Utopias & speculative fiction",
    "Lo! Looking Backwards": "Fortean & psychical research",
    "Lore of the Unicorn": "Vampires, monsters & strange creatures",
    "Wisdom of the Ages": "New Thought",
    "Etidorhpa": "Hollow earth & alternative cosmologies",
    "Stolen Legacy": "Ancient Egypt",
    "Wonderful Ethiopians of the Ancient Cushite Empire": "Africa & the African diaspora",
    "Alexandrines": "Classical myth & literature",
    'Emerald Tablet of Hermes': 'Hermeticism & alchemy',
    'Isiac Tablet of Cardinal Bembo, The': 'Ancient Egypt',
    'Seven Tablets of Creation, The': 'Ancient Near East',
    'Buddhist Bible, A': 'Buddhism',
    "Hortulanus' Commentary on the Emerald Tablet": 'Hermeticism & alchemy',
    "John Wesley's Place in History": 'Christianity',
    'Notes on the Folk-Lore of the North-East of Scotland': 'Celtic',
    'Notes on the Folklore of the Fjort': 'Africa & the African diaspora',
    'Notes on the Shoshonean Dialects of Southern California': 'Native American',
    'Oahspe, A Kosmon Bible in the Words of Jehovih and his Angel Embassadors': 'New religious movements',
    'Psalms of the Sisters': 'Buddhism',
    "Will and Testament of 'Abdu'l-Baha, The": "Bahá'í Faith",
    'Abortion in the Bible': 'Age of Reason & freethought',
    'Absurdities of the Bible': 'Age of Reason & freethought',
    'Self-Contradictions of the Bible': 'Age of Reason & freethought',
    'Jefferson Bible, The': 'Age of Reason & freethought',
    'Decline and Fall of the Roman Empire, Vol. 1': 'Classical myth & literature',
    'Fairy Tales of Modern Greece': 'European folklore & fairy tales',
    'From Ritual To Romance': 'Comparative religion & anthropology',
    'Golden Chain of Homer': 'Hermeticism & alchemy',
    'Heroic Romances of Ireland (2 Vols.)': 'Celtic',
    'Legends and Romances of Brittany': 'Celtic',
    'Legends and Romances of Spain': 'European folklore & fairy tales',
    'Popular Romances of the West of England': 'Celtic',
    'Orpheus, Myths of the World': 'Comparative religion & anthropology',
    'Rig Veda Americanus (Aztec Hymns)': 'Native American',
    'Isis Unveiled': 'Theosophy & occultism',
    'Veil of Isis or Mysteries of the Druids, The': 'Celtic',
    'Oriental Religions in Roman Paganism, The': 'Classical myth & literature',
    'Egyptian Heaven and Hell, The': 'Ancient Egypt',
    'Egyptian Heaven and Hell, Vol. I: The Book of the Am-Tuat, The': 'Ancient Egypt',
    'Egyptian Heaven and Hell, Vol. II: The Book of Gates, The': 'Ancient Egypt',
    'Egyptian Heaven and Hell, Vol. III: The Egyptian Heaven and Hell, The': 'Ancient Egypt',
    'Golden Tractate of Hermes Trismegistus, The': 'Hermeticism & alchemy',
    'New Atlantis, The': 'Utopias & speculative fiction',
    'Pagan Christs: Studies in Comparative Hierology': 'Comparative religion & anthropology',
    'Pagan and Christian Creeds': 'Comparative religion & anthropology',
    'Golden Bough, The': 'Comparative religion & anthropology',
    'English and Scottish Popular Ballads, The': 'European folklore & fairy tales',
    'Harmonies of the World': 'Philosophy (modern)',
    'Heroic Enthusiasts, The': 'Philosophy (modern)',
    "Bulfinch's Mythology": "Comparative religion & anthropology",
    "Complete Sayings of Jesus, The": "Christianity",
    "Dancing Gods": "Native American",
    "Dawn of a New Day, The": "Bahá'í Faith",
    "Dawn of the World, The": "Native American",
    "Discourses, The": "Classical philosophy",
    "Doctrine of the Last Things, The": "Christianity",
    "Essay on Dream, An": "Theosophy & occultism",
    "Form and the Dance Drama": "Native American",
    "Goal of Life, The": "New Thought",
    "House of the Hidden Places, The": "Earth mysteries",
    "Kybalion, The": "Hermeticism & alchemy",
    "Letter from a Gentleman, A": "Christianity",
    "Myths and Legends of California and the Old Southwest": "Native American",
    "Myths and Legends of Our Own Land": "Native American",
    "New England Primer": "Christianity",
    "New Word, The": "Theosophy & occultism",
    "Paradoxes of the Highest Science": "Theosophy & occultism",
    "Promised Key, The": "Africa & the African diaspora",
    "Prophets, Their Lives and Their Stories, The": "Judaism",
    "Sacred Fire, The": "Sacred sexuality",
    "Story of Gio, The": "Shinto & Japan",
    "Studies from an Eastern Home": "Literature & poetry",
    "Summer Legends": "Native American",
    "Unveiling a Parallel": "Utopias & speculative fiction",
}
CHRISTIAN = r"Christ|Church|Catechism|Creed|Nicene|Ante-Nicene|Saint|St\.|Saints|Lord's Prayer|Hail Mary|Mass|Popes|Martyrs|Bede|Calvin|Luther|Wesley|Westminster|Heidelberg|Helvetic|Barmen|Dordrecht|Synod|Pilgrim's Progress|Bunyan|Passion|Augustine|Anselm|Ignatius|Francis|Charnock|Unitarian|Second Coming|Enemies of the Cross|Man of Sorrows|God the Savior|Of Prayer|Of The Office of Preaching|On Faith|Wheat & The Tares|Parable of the Sower|Twofold Use|Large Catechism|Small Catechism|Church Order|Liturgy|Hymns of the Eastern Church|Gospel|Trial of Christ|Oberammergau|Lives of the Saints|Book of Revelation"
LITERATURE = r"Arabian Nights|Chaucer|Dante|Milton|Spenser|Tennyson|Blake|Ballad|Poems|Poetry|Epic|Sonnets|Faerie|Dracula|Romance|Tales$|Christmas|Fables"


def classify(title: str) -> str:
    if title in OVERRIDES:
        return OVERRIDES[title]
    if title in SHAKESPEARE:
        return "Shakespeare"
    if title in PLATO_ETC:
        return "Classical philosophy"
    if title in GREEK_DRAMA:
        return "Classical myth & literature"
    for subject, rx in RULES:
        if re.search(rx, title):
            return subject
    if re.search(CHRISTIAN, title):
        return "Christianity"
    if re.search(LITERATURE, title):
        return "Literature & poetry"
    if title.startswith("Decline and Fall"):
        return "Literature & poetry"
    return "Other"


def sort_key(title: str) -> str:
    t = re.sub(r",\s*(The|A|An)$", "", title)
    return re.sub(r"^[^\w]+", "", t).lower()


def search_url(title: str) -> str:
    """A web search restricted to sacred-texts.com. The archive's own pages have stable but
    unpredictable addresses, so we link a site search rather than guess them."""
    t = re.sub(r",\s*(The|A|An)$", "", title)
    return "https://duckduckgo.com/?q=" + quote_plus(f'site:sacred-texts.com "{t}"')


def load() -> list[dict]:
    rows, seen = [], set()
    for line in TITLES.read_text("utf-8").splitlines():
        title = line.strip()
        if not title or title.startswith("#") or title in seen:
            continue
        seen.add(title)
        subj = classify(title)
        rows.append({"title": title, "subject": subj, "section": SUBJECTS[subj][0], "url": search_url(title)})
    rows.sort(key=lambda r: sort_key(r["title"]))
    return rows


if __name__ == "__main__":
    from collections import Counter
    rows = load()
    c = Counter(r["subject"] for r in rows)
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        print(f"{v:5}  {k}")
    print(len(rows), "titles")
    other = [r["title"] for r in rows if r["subject"] == "Other"]
    if other:
        print("\nUnclassified:\n  " + "\n  ".join(other))
