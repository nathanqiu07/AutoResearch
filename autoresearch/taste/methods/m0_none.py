from ..usermodel import UserModel


class NoHistory(UserModel):
    method_id = "m0"

    def predict(self, context, options):
        return self._predict_with(context, options)
