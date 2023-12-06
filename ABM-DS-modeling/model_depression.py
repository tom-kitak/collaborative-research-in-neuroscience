from BPTK_Py import Agent
from BPTK_Py import Model
from BPTK_Py import DataCollector
from BPTK_Py import SimultaneousScheduler
import random


class Person(Agent):
    def initialize(self):
        self.agent_type = "person"
        self.state = "healthy"
        # Options: depression, healthy, depression_treated, depression_untreated, healthy_treated

    def act(self, time, round_no, step_no):
        act_of_god = random.random()
        if self.state == "healthy":
            if act_of_god < 0.3:
                self.state = "depression"
        if self.state == "depression_untreated":
            if act_of_god < 0.05:
                self.state = "healthy"

    def __repr__(self):
        return self.state


class DepressionTreatmentSD:
    def __init__(self, model):
        self.model = model

        # Stock
        self.treated = model.stock("treated")

        # Flow
        self.incoming_patients = model.flow("incoming_patients")
        self.outgoing_patients = model.flow("outgoing_patients")

        # Converters
        self.patient_demand = model.converter("patient_demand")
        self.enter_treatment = model.converter("enter_treatment")
        self.untreated = model.converter("untreated")

        # Constants
        self.treatment_success_rate = model.constant("treatment_success_rate")
        self.enter_treatment_rate = model.constant("enter_treatment_rate")

        # Functions
        # We are using time parameter to pass demand information -> very sus >:| but I don't know how else to pass info
        update_function = model.function("update_function", lambda m, t: t)

        # Equations
        self.treated.equation = self.incoming_patients - self.outgoing_patients
        self.incoming_patients.equation = self.enter_treatment
        self.outgoing_patients.equation = self.treated * self.treatment_success_rate
        self.patient_demand.equation = update_function()
        self.enter_treatment.equation = self.enter_treatment_rate * self.patient_demand
        self.untreated.equation = (1 - self.enter_treatment_rate) * self.patient_demand

        # Initial values
        self.treated.initial_value = 0.0


class DepressionTreatmentHybrid(Model):
    def instantiate_model(self):
        super().instantiate_model()
        self.register_agent_factory("person", lambda agent_id, model, properties: Person(agent_id, model, properties))
        self.sd_model = DepressionTreatmentSD(self)

    def configure(self, config):
        super().configure(config)

        self.sd_model.treatment_success_rate.equation = self.treatment_success_rate
        self.sd_model.enter_treatment_rate.equation = self.enter_treatment_rate

    def begin_round(self, time, sim_round, step):

        depression_demand = 0
        update_enter_treatment = int(self.evaluate_equation("enter_treatment", time))
        update_untreated = int(self.evaluate_equation("untreated", time))
        update_outgoing_patients = int(self.evaluate_equation("outgoing_patients", time))

        for agent in self.agents:
            if agent.state == "depression":
                depression_demand += 1
                if update_enter_treatment > 0:
                    agent.state = "depression_treated"
                    update_enter_treatment -= 1
                elif update_untreated > 0:
                    agent.state = "depression_untreated"
                    update_untreated -= 1
            elif agent.state == "depression_treated":
                if update_outgoing_patients > 0:
                    agent.state = "healthy_treated"
                    update_outgoing_patients -= 1

        self.sd_model.patient_demand(depression_demand)


if __name__ == "__main__":
    depression_treatment_hybrid = DepressionTreatmentHybrid(name="Fucking work srot poceasen",
                                                            scheduler=SimultaneousScheduler(),
                                                            data_collector=DataCollector())

    depression_treatment_hybrid.instantiate_model()

    depression_treatment_hybrid_config = {
        "runspecs": {
            "starttime": 1,
            "stoptime": 10,
            "dt": 1.0
        },
        "properties":
            {
                "treatment_success_rate":
                    {
                        "type": "Double",
                        "value": 0.5
                    },
                "enter_treatment_rate":
                    {
                        "type": "Double",
                        "value": 0.8
                    },
            },
        "agents":
            [
                {
                    "name": "person",
                    "count": 100
                }
            ]
    }

    depression_treatment_hybrid.configure(depression_treatment_hybrid_config)
    depression_treatment_hybrid.run()

    results = depression_treatment_hybrid.statistics()

    for t, r in results.items():
        r = dict(sorted(r["person"].items()))
        print(f"T:{t}={r}")
