import numpy as np
# from enum import enum

class Prescription:
    def __init__(self):
        """
         Default constructor for a prescription.
            Prescription contains a
                drug_name,
                unit_of_admin,
                quantity_of_admin,
                frequency,
                unit_of_frequency,
                strength,
                duration,
                unit_of_duration
        """
        self.drug_name = ""
        self.unit_of_admin = ""
        self.quantity_of_admin = ""
        self.frequency = ""
        self.unit_of_frequency = ""
        self.strength = ""
        self.duration = ""
        self.unit_of_duration = ""

    def __init__(self,
                 drug_name,
                 unit_of_admin,
                 quantity_of_admin,
                 frequency,
                 unit_of_frequency,
                 strength, duration,
                 unit_of_duration):
        """
        Prescription Constructor
        :param drug_name: String, name of drug, all caps
        :param unit_of_admin: String, Unit of Administration (Capsule, Tablet, Milligram, etc)
        :param quantity_of_admin: Numeric, Quantity of Administration (1 capsule, 3 tablets)
        :param frequency: Numeric, frequency at which to take drug
        :param unit_of_frequency: String, Frequency unit (1 time per day, every 6 hours, etc)
        :param strength: String, Dispense Strength (500mg Capsule, 20mg Tablet, etc)
        :param duration: String, Duration of drug use
        :param unit_of_duration: String unit of Duration (For 30 days, for 12 hours, etc)
        """
        self.drug_name = drug_name
        self.unit_of_admin = unit_of_admin
        self.quantity_of_admin = quantity_of_admin
        self.frequency = frequency
        self.unit_of_frequency = unit_of_frequency
        self.strength = strength
        self.duration = duration
        self.unit_of_duration = unit_of_duration

    def __str__(self):
        """return human-readable string representation of this prescription"""
        return "{}: Take {} {} every {} {} for {} {} for {} {}".format(self.drug_name,
                                                                       self.quantity_of_admin,
                                                                       self.unit_of_admin,
                                                                       self.frequency,
                                                                       self.unit_of_frequency,
                                                                       self.duration,
                                                                       self.unit_of_duration)

    def __eq__(self, other):
        """Compare prescriptions - check all parameters match"""
        if isinstance(other, Prescription):
            return (self.drug_name == other.drug_name and
                    self.unit_of_duration == other.unit_of_duration and
                    self.duration == other.duration and
                    self.unit_of_frequency == other.unit_of_frequency and
                    self.frequency == other.frequency and
                    self.unit_of_admin == other.unit_of_admin and
                    self.quantity_of_admin == other.quantity_of_admin and
                    self.strength == other.strength)
        elif isinstance(other, str):
            return str(self) == other
        else:
            return False


class AdministrationSchedule:
    """
    Administration schedule holds a list of prescriptions
    """
    def __init__(self):
        self.prescriptionList = []

    def add_prescription(self, newPrescription):
        self.prescriptionList.append(newPrescription)

    def __str__(self):
        outstr = ""
        for scrip in self.prescriptionList:
            outstr = outstr + str(scrip)
        return outstr

class frequency:
    def __init__(self):
        self.value = 0
        self.modifier = "PER" # Options are "Every" as in "Every 2 hours" and "Per" as in "Per Day"
        self.period = 1
        self.pvalue = "DAYS"

    def __init__(self,
                 value,
                 modifier,
                 period,
                 pvalue):
        self.value = value
        self.modifier = modifier
        self.period = period
        self.pvalue = pvalue

    def __str__(self):
        return "{} {} {} {}".format(self.value, self.modifier, self.period, self.pvalue)



