from nltk import pos_tag
from nltk import word_tokenize
from nltk import RegexpParser
from nltk import RegexpChunkParser
from nltk import tag
from nltk import UnigramTagger
from nltk import DefaultTagger
import cv2
import pytesseract
import prescriptions
import numpy as np
import label_unwrap


class PrescriptionParser:



    # Process the frequency chunk
    @staticmethod
    def __parse_freq_chunk(fq_chunk):
        for itm in fq_chunk:
            print(itm)



    # individual parsing methods are pulled out to their own functions
    # This de-clutters the code and allows individual tuning
    @staticmethod
    def string_to_prescription(s):
        """
        Static method to convert a string to a structured prescription
        Use NLTK to do the following:
            Tokenize the string
            Clean up and lemmatize the tokens
            Identify the following groups:
                Drug name
                Drug Strength
                Dispensation / Presentation unit (EG Tablet, capsule)
                Frequency & Unit (EG twice per day)
                Total Quantity
                Duration (may be calculated from dose/frequency/total

        :param s: Input string - EG "Take 2 500mg tablets acyclovir once per day with food for 3 days"
        :return: Structured Prescription object
        """
        script_stopwords = ["(", ")", ",", "AND"]

        # Clean up the string
        s = s.upper()

        prescription_model = {}

        #Set up NLTK parser from our custom tagged corpus
        file = open('tagged_script_corpus', 'r')
        # Read lines from the tagged prescription model corpus
        # into a dictionary, create a tagging model.

        for fl_line in file:
            mod_key = tag.str2tuple(fl_line)
            # print("Key: ", mod_key[0])
            # print("Value:", mod_key[1])
            prescription_model[mod_key[0]] = mod_key[1].strip()
        file.close()

        # Create an NTLK Unigram Tagger to identify prescription-specifc words

        # Tag likely prescription words using a custom unigram tag model
        # Tag all unkown words (not frequency, drug or route) as 'UK'
        # We'll reconcile the 2 taggers in a minute
        scrip_tagger = UnigramTagger(model=prescription_model, backoff=DefaultTagger('UK'))

        # Use NLTK to split, chunk and tag the input string
        text = word_tokenize(s)
        filtered_script = []
        #filter un-needed stopwords and punctuation
        for w in text:
            if w not in script_stopwords:
                filtered_script.append(w)

        # print("After Split:", text)
        tagged1 = scrip_tagger.tag(filtered_script)
        # print("Tokens 1: ", tagged1)
        tokens_tag = pos_tag(filtered_script)
        # print("After Token:", tokens_tag)
        i = 0

        # Reconcile the 2 taggers
        # Items tagged as UK are not recognized by our prescription model, and should be over-written
        # with the values from the default Perceptron tagger
        # As the current Perceptron Tagger is not an extension of Unigram tagger, it cannot be used as a backoff
        for stk in tagged1:
            if stk[1] != "UK":
                tokens_tag[i] = stk
            i += 1

        rt_chunker = r"""
        Route: {<NNP.?>*<RT.?>+ || <IN>+<CC>?<RT>?}
        Dose: {<VB.?>*<CD.?>*<AD.?>+}
        }<FQM.?|FQ>+{
        Dur: {<DR>+<CD>*<FQ>+}
        Freq: {<CD||MD>*<FQM>+<FQ>+ || <FQM>+<CD|JJ>+<FQ>+ || <MD>+<FQM>+ || <CD>+<FQM>+ || <FQM>+<TM>+ || <NNP>+<TM>+ || <FQM>}
        }<DR>+{
        """
        rtParser = RegexpParser(rt_chunker)
        route_chunk = rtParser.parse(tokens_tag)
        # route_chunk.draw()
        #print(route_chunk)
        #print(s)
        for stree in route_chunk.subtrees():
            if stree.label() == "Freq":
                #print("\t", "Frequency: ", stree)
                #print(PrescriptionParser.__parse_freq_chunk(stree))
                return PrescriptionParser.__parse_freq_chunk(stree)
        return ""



    @staticmethod
    def parse_drug_name(input_string):
        script_stopwords = ["(", ")", ",", "AND"]
        s = input_string.upper()
        file = open('tagged_script_corpus', 'r')
        text = word_tokenize(s)
        for word in text:
            candidate_drg_name = PrescriptionParser.check_drug_name(word)
            if candidate_drg_name != "":
                return candidate_drg_name
        return ""

    @staticmethod
    def calculate_lev_distance(p, q):
        """
            Calculate the Levenstein distance between 2 strings, P and Q
            This is used to find close / probable matches between strings when an exact match can't be
            found

            The Levenstein distance is the integer number of insertions, deletions and letter changes needed to
            convert string p into string q.
            EG: CalculateLevDistance("far", "for") == 1
                CalculateLevDistance("a", "bbbb") == 4
                CalculateLevDistance("foo", "foo") == 0
        :param p: Input String 1
        :param q: Input String 2
        :return: integer Levenshtein distance
        """
        mtx_lev_distance = np.zeros((len(p)+1, len(q)+1))
        for c in range(len(p) + 1):
            mtx_lev_distance[c, 0] = c

        for c in range(len(q) + 1):
            mtx_lev_distance[0, c] = c

        a = 0
        b = 0
        c = 0

        for cp in range(1, len(p) + 1):
            for cq in range(1, len(q) + 1):
                if p[cp - 1] == q[cq - 1]:
                    mtx_lev_distance[cp][cq] = mtx_lev_distance[cp - 1][cq - 1]
                else:
                    a = mtx_lev_distance[cp][cq - 1]
                    b = mtx_lev_distance[cp - 1][cq]
                    c = mtx_lev_distance[cp - 1][cq - 1]
                    if a <= b and a <= c:
                        mtx_lev_distance[cp][cq] = a + 1
                    elif b <= a and b <= c:
                        mtx_lev_distance[cp][cq] = b + 1
                    else:
                        mtx_lev_distance[cp][cq] = c + 1

        return mtx_lev_distance[len(p)][len(q)]

    @staticmethod
    def check_drug_name(s):
        """
        Take in a string, check if it's likely to be a drug name
        To account for potential typos, shortening, or mis-translations
        in image-to-text process the following
        rules are used:
            If s is in the drug name file, return true
            if s is not in the drug name file, check by Levenstein distance
                If there is a word in the drug name file which differs by no more than 15% of characters, return true
            else return false

        Direct matches are significantly cheaper to check - Levenstein's algorithm is expensive
        So those are checked first
        :param s: Input candidate drug name
        :return: true if the name is likely the prescription's drug name
        """
        # Clean up / Pre-Process the string
        s = s.lower().replace(" ", "").replace(".", "").replace("-", "").replace(",", "").replace(".", "")
        file = open('fda_drug_list', 'r')
        lines = file.readlines()
        file.close()
        for ln in lines:
            if s == ln.strip():
                # This is an authoritative match
                # Return the original string
                return s

        for ln in lines:
            lev_dist = PrescriptionParser.calculate_lev_distance(s, ln.strip())
            if (lev_dist / len(s)) < .15:
                # This is a probable match
                # since it is not an exact match, return the value identified by lev. distance
                # this prevents cases like "wescitalopram", instead correctly returning "ESCITALOPRAM"
                return ln.strip()

        return ""


    @staticmethod
    def __parse_freq_chunk(fchunk):
        """
        Take a split-and-tagged section of a prescription, return a list of drug administration times
        Times may be a specific time (10AM, 11PM), or a named time "BREAKFAST". Return ERROR if a valid
        frequency cannot be determined
        :param fchunk: Tagged chunk of a prescription, presented as a tree
        :return: list of string times
        """
        try:
            times_per_day = 0
            fq_val = []
            fq_term = []
            fq_mod = []
            fq_digits = []
            fq_specified_times = []

            for token in fchunk:
                if token[1] == "CD":
                    # print("Cardinal Frequency")
                    if not (token[0].isnumeric()):
                        # This is a word number - EG "ONE", "TWO"
                        parsed_num = PrescriptionParser.str2int(token[0])
                    else:
                        parsed_num = int(token[0])
                    fq_digits.append(parsed_num)
                    # print("Parsed Number: ", parsed_num)

                elif token[1] == "FQ":
                    fq_term = token[0]
                elif token[1] == "FQM":
                    fq_mod = token[0]
                elif token[1] == "TM":
                    if token[0] == "AM" or token[0] == "PM":
                        fq_specified_times.append(fchunk[fchunk.index(token[0])-1][0] + token[0])

                    else:
                        fq_specified_times.append(token[0])
                elif token[1] == "OD":
                    fq_digits.append(token[0])
                elif token[1] == "MD":
                    parsed_num = PrescriptionParser.multnum2int(token[0])
                    fq_digits.append(parsed_num)
                elif token[1] == "JJ" and token[0].__contains__("-"):
                    # indicates there is a range value... Use the lower value to create the most possible divisions
                    # Generally indicates "4 - 6 hours", so lower values gives the most permissive dosing schedule
                    splt_digits = token[0].split("-")
                    min = 0
                    for digit in splt_digits:
                        int_digit = PrescriptionParser.str2int(digit)
                        if min == 0 or int_digit < min:
                            min = int_digit
                    if min > 0:
                        fq_digits.append(min)
                    # print("Range Value")

            # TIMES/FQM
            # PER/FQM
            # EVERY/FQM
            if len(fq_mod) == 0 and len(fq_specified_times) == 0:
                # The only case that this is valid is if specific times are provided
                return ["ERROR"]

            if len(fq_digits) == 0 and not ( fq_mod.__contains__("DAILY") or fq_mod.__contains__("AT") or len(fq_specified_times) > 0 or (fq_mod.__contains__("EVERY") and fq_term.__contains__("DAY"))):
                return ["ERROR"]

            if fq_mod.__contains__("PER"):
                if len(fq_val) == 0:
                    return ["ERROR"]
                if fq_val[0] == "DAY":
                    fq_specified_times = PrescriptionParser.times_from_digits(fq_digits[0])
                else:
                    return ["ERROR"] # "PER" should really only occur as "Per Day"
            elif fq_mod.__contains__("EVERY"):
                if fq_term.__contains__("DAY"):
                    # Check the cardinal values provided
                    if len(fq_digits) > 0:
                        fq_specified_times = PrescriptionParser.times_from_digits(fq_digits[0])
                    else:
                        fq_specified_times.append("BREAKFAST")
                elif fq_term.__contains__("HOURS"):
                    if len(fq_digits) > 0:
                        fq_specified_times = PrescriptionParser.every_x_hours(fq_digits[0])
                    else:
                        return ["ERROR"]
                elif len(fq_specified_times) > 0:
                    return fq_specified_times
                else:
                    fq_specified_times.append("ERROR")
            elif fq_mod.__contains__("DAILY"):
                if len(fq_digits) == 0:
                    fq_digits.append(1) # The phrase "daily" is an exception implying once daily, but all others must specify a number of times
                fq_specified_times = PrescriptionParser.times_from_digits(fq_digits[0])
            elif fq_mod.__contains__("TIMES"):
                if fq_term.__contains__("DAY"):
                    fq_specified_times = PrescriptionParser.times_from_digits(fq_digits[0])
                else:
                    return ["ERROR"]
            elif fq_mod.__contains__("WITH"):
                if len(fq_specified_times) == 0:
                    return ["ERROR"]

            out = PrescriptionParser.process_synonyms(fq_specified_times)
            return out
        except ValueError:
            return ["ERROR: Invalid Input"]
        except RuntimeError:
            return ["ERROR: RuntimeError"]


    @staticmethod
    def times_from_digits(tm_count):
        """
        Given a tm_count integer representing "times per day" in any variation
        return a list of appropriate values

        :return:
        """
        fq_specified_times = []

        if tm_count == 1:
            fq_specified_times.append("BREAKFAST")  # If only one time per day, assume Breakfast
        elif tm_count == 2:
            fq_specified_times.append("BREAKFAST")
            fq_specified_times.append("DINNER")
        elif tm_count == 3:
            fq_specified_times.append("BREAKFAST")
            fq_specified_times.append("LUNCH")
            fq_specified_times.append("DINNER")
        elif 3 < tm_count <= 12:
            # Divide 24h evenly by fq_digits[0]
            fq_specified_times.append("")
        else:
            fq_specified_times.append("ERROR")
        return fq_specified_times

    @staticmethod
    def str2int (s_num):
        """
        Convert a single integer as spelled out into an integer value
        EG: TWO -> 2, THREE -> 3
        :param s_num: string representation of a single digit
        :return: "ERROR" if invalid, integer digit 0-9 else
        """""
        if s_num.isnumeric():
            return int(s_num)

        ints = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]

        if not ints.__contains__(s_num.lower()):
            return "ERROR"
        return ints.index(s_num.lower())

    @staticmethod
    def multnum2int(s_num):
        """
        Convert a single multiplicative number as spelled out into an integer value
        EG: once -> 1, twice -> 2, thrice -> 3
        :param s_num: string representation of a single digit
        :return: "ERROR" if invalid, integer digit 0-3 else
        """""

        ints = ["never", "once", "twice", "thrice"]

        if not ints.__contains__(s_num.lower()):
            return "ERROR"
        return ints.index(s_num.lower())

    @staticmethod
    def every_x_hours(x_hours):
        curr_time = 0
        out = []

        while curr_time <= (24 - x_hours):
            curr_time += x_hours
        #    if curr_time > 12:
        #        out.append((curr_time - 12).__str__() +  "AM")
        #    elif curr_time == 12:
        #        out.append("12PM")
        #    else:
        #        out.append(curr_time.__str__() + "AM")
            if curr_time == 24:
                out.append("00:00:00")
            else:
                out.append(curr_time.__str__() + ":00:00")
        return out

    @staticmethod
    def process_synonyms(time_list):
        file = open('time_synonyms', 'r')
        lines = file.readlines()
        file.close()
        syns = {}
        out = []
        for ln in lines:
            splt = ln.split("/")
            word = splt[0].strip()
            syn = splt[1].strip()
            syns[word] = syn
        for time in time_list:
            if syns.__contains__(time):
                out.append(syns[time])
            else:
                out.append(time)
        return out



    @staticmethod
    def process_image(temp_img_name):
        # Set up PyTeseract
        pytesseract.pytesseract.tesseract_cmd = 'Tesseract/tesseract.exe'
        # window = cv2.namedWindow('Display Demo', cv2.WINDOW_NORMAL)
        # Open Image
        img = cv2.imread(temp_img_name)
        # Convert to Grayscale
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # cv2.imshow("Display Demo", img_gray)
        # cv2.waitKey(0)
        # cv2.destroyWindow("Image")

        # Threshold for conversion
        # ret, thresh1 = cv2.threshold(img_gray, 0, 255, cv2.THRESH_OTSU)
        thresh1 = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        # cv2.imshow("Display Demo", thresh1)
        # cv2.waitKey(0)
        # cv2.destroyWindow("Display Demo")
        tesseract_config_string = "-c tessedit_char_whitelist='.,-01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz '"
        extracted_text = pytesseract.image_to_string(img_gray, config=tesseract_config_string)
        return extracted_text.replace("\n", " ")
        # return extracted_text

    @staticmethod
    def flatten_image(img_path, shape):
        img_root = img_path.replace(".jpg", "")
        points = []

        for point in shape['shape']:
           points.append([point['x'], point['y']])
        imcv = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        unwrapper = label_unwrap.LabelUnwrapper(src_image=imcv, percent_points=points)
        # unwrapper.calc_label_points(img_path)
        dst_image = unwrapper.unwrap(interpolate=True)
        # for point in unwrapper.points:
        #  cv2.line(unwrapper.src_image, tuple(point), tuple(point), color=label_unwrap.YELLOW_COLOR, thickness=3)

        # unwrapper.draw_mesh()

        # cv2.imwrite(img_root + "_meshed.png", imcv)
        cv2.imwrite(img_root + "_unwrapped.jpg", dst_image)
